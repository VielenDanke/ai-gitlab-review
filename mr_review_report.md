### Review of Changes

#### File: `internal/data/error/error.go`

**Changes Summary:**
- Added a new error code `ExcessOfCompassCommentCharacters` with value 3355.
- Updated the `GrpcCode` map to include this new error code, mapping it to gRPC code 5.

**Analysis:**
1. **Bugs Introduced:** None identified. The addition of a new error code and its corresponding gRPC mapping appears correct.
2. **Security Vulnerabilities:** No security issues detected in these changes.
3. **Code Style/Maintainability:** The code remains clean and maintainable. Adding the new error code follows existing patterns.

---

#### File: `internal/services/core/resolve.go`

**Changes Summary:**
- Modified the function signature of `formCheckCompassRequestComment` to include additional parameters (`ctx context.Context`, `stage *models.Stage`, `step *models.Step`) and now returns a tuple `(string, error)`.
- Added logic to check if the comment exceeds 750 characters. If it does:
  - Logs a warning.
  - Creates an error using `errs.New` with the new error code `ExcessOfCompassCommentCharacters`.
  - Calls `r.failureService.FailTransferStageStep` and returns an error.

**Analysis:**
1. **Bugs Introduced:**
   - The function `formCheckCompassRequestComment` is called in `compassCheckP2pTransfer` with incorrect arguments:
     ```go
     comment, currencyMapResponseErr := r.formCheckCompassRequestComment(ctx, transfer, sourceCardProduct, destinationCardProduct, resolveStep.Stage, compassCheckP2pTransfer)
     ```
     Here, the last argument is `compassCheckP2pTransfer`, which appears to be a string or similar type, but the function expects a pointer to `*models.Step`. This will cause a type mismatch and potential runtime errors.
   - If an error is returned from `formCheckCompassRequestComment`, the comment is set to an empty string. However, the caller (`compassCheckP2pTransfer`) uses this comment in the request without validation, which could lead to unintended behavior.

2. **Security Vulnerabilities:** No security issues detected in these changes.
3. **Code Style/Maintainability:**
   - The addition of error handling for comment length is a positive change but introduces complexity.
   - The function `formCheckCompassRequestComment` now has side effects (calling `r.failureService.FailTransferStageStep`), which could make the code harder to test and debug.

---

### Final Status

The changes in `resolve.go` introduce bugs due to incorrect function arguments and potential issues with error handling. These need to be addressed before merging.

****