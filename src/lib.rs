use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use ssdeep::{FuzzyHash, FuzzyHashCompareTarget};

// Upstream handles syntax, size constraints, and comparison normalization.
// Require full consumption: our API accepts fingerprints, not ssdeep CSV rows.
fn parse(value: &str) -> Result<FuzzyHash, String> {
    let mut end = 0;
    let hash = FuzzyHash::from_bytes_with_last_index(value.as_bytes(), &mut end)
        .map_err(|err| format!("invalid fingerprint: {err}"))?;
    if end != value.len() {
        return Err("invalid fingerprint: trailing filename or data is not accepted".into());
    }
    Ok(hash)
}

fn scan(
    target: &FuzzyHashCompareTarget,
    candidates: &[String],
    threshold: u32,
) -> Result<Option<(usize, u32)>, String> {
    for (index, candidate) in candidates.iter().enumerate() {
        let parsed = parse(candidate).map_err(|err| format!("candidates[{index}]: {err}"))?;
        let score = target.compare(parsed);
        if score >= threshold {
            return Ok(Some((index, score)));
        }
    }
    Ok(None)
}

/// Hash bytes without content normalization.
#[pyfunction]
fn hash(py: Python<'_>, data: &Bound<'_, PyBytes>) -> PyResult<String> {
    // PyBytes is immutable and the bound argument keeps it alive while detached.
    let bytes = data.as_bytes();
    py.detach(|| ssdeep::hash_buf(bytes).map(|hash| hash.to_string()))
        .map_err(|err| PyValueError::new_err(format!("cannot hash data: {err}")))
}

/// Compare two fingerprints, returning the upstream score in 0..=100.
#[pyfunction]
fn compare(py: Python<'_>, left: &str, right: &str) -> PyResult<u32> {
    py.detach(|| Ok(parse(left)?.compare(parse(right)?)))
        .map_err(|err: String| PyValueError::new_err(err))
}

/// An immutable prepared target reusable across bounded candidate batches.
#[pyclass(frozen, module = "fuzzbite._native")]
struct Matcher {
    target: FuzzyHashCompareTarget,
}

#[pymethods]
impl Matcher {
    #[new]
    fn new(fingerprint: &str) -> PyResult<Self> {
        let parsed = parse(fingerprint).map_err(PyValueError::new_err)?;
        Ok(Self {
            target: FuzzyHashCompareTarget::from(&parsed),
        })
    }

    /// Return the first (batch index, score) meeting threshold, or None.
    /// All items are copied as strings first; syntax is checked only up to a match.
    #[pyo3(signature = (candidates, *, threshold=90))]
    fn find_match(
        &self,
        py: Python<'_>,
        candidates: Vec<String>,
        threshold: i64,
    ) -> PyResult<Option<(usize, u32)>> {
        if !(0..=100).contains(&threshold) {
            return Err(PyValueError::new_err("threshold must be between 0 and 100"));
        }
        // Only owned strings and immutable Rust state enter the detached closure.
        py.detach(|| scan(&self.target, &candidates, threshold as u32))
            .map_err(PyValueError::new_err)
    }
}

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(hash, module)?)?;
    module.add_function(wrap_pyfunction!(compare, module)?)?;
    module.add_class::<Matcher>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reference_and_prepared_scanning() {
        let left = parse("12288:+ySwl5P+C5IxJ845HYV5sxOH/cccccccei:+Klhav84a5sxJ").unwrap();
        let right = "12288:+yUwldx+C5IxJ845HYV5sxOH/cccccccex:+glvav84a5sxK";
        let target = FuzzyHashCompareTarget::from(&left);
        assert_eq!(target.compare(parse(right).unwrap()), 88);
        assert_eq!(scan(&target, &[], 0), Ok(None));
        assert_eq!(scan(&target, &[right.into()], 89), Ok(None));
        assert_eq!(
            scan(&target, &[right.into(), "bad".into()], 88),
            Ok(Some((0, 88)))
        );
        assert!(scan(&target, &["bad".into()], 0)
            .unwrap_err()
            .contains("[0]"));
    }

    #[test]
    fn parser_requires_a_complete_bounded_fingerprint() {
        for bad in ["", "4:abc:abc", "3:a:b,file", "3:a:b\0", "3:é:b"] {
            assert!(parse(bad).is_err(), "{bad:?}");
        }
        assert!(parse(&format!("3:{}:", "a".repeat(65))).is_err());
        assert!(parse(&format!("3::{}", "a".repeat(33))).is_err());
        assert!(parse("3::").is_ok());
        assert_eq!(
            ssdeep::hash_buf(b"hello world").unwrap().to_string(),
            "3:iKFSMPn:rJPn"
        );
    }
}
