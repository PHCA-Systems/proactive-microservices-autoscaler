# Task 3.1 Implementation: Create Experiment Launcher

## Summary

Successfully implemented the `launch_experiment_suite()` function in `pipeline_orchestrator.py` that launches the experiment suite as a background process with real-time log monitoring.

## Implementation Details

### Function Signature
```python
def launch_experiment_suite(
    experiment_config: ExperimentConfig,
    log_file_path: Optional[str] = None
) -> subprocess.Popen
```

### Key Features Implemented

1. **Subprocess Invocation**
   - Uses `subprocess.Popen` for background execution
   - Returns process handle for monitoring
   - Non-blocking execution

2. **Unbuffered Output**
   - Uses `python -u` flag for unbuffered output
   - Enables real-time log file updates
   - Critical for progress monitoring

3. **Log File Redirection**
   - Redirects stdout/stderr to `experiment_run_log.txt`
   - Default location: `kafka-structured/experiments/experiment_run_log.txt`
   - Supports custom log file path via parameter
   - Line-buffered for real-time updates

4. **No Pause Flag**
   - Does NOT pass `--pause-before-start` flag
   - Experiments start immediately
   - As per design requirements

5. **Error Handling**
   - Checks if `run_experiments.py` exists
   - Raises `FileNotFoundError` if script missing
   - Creates log directory if needed

### Process Handle Capabilities

The returned `subprocess.Popen` handle provides:
- `process.pid` - Process ID
- `process.poll()` - Check if still running
- `process.wait()` - Wait for completion
- `process.terminate()` - Graceful termination
- `process.kill()` - Force termination
- `process.returncode` - Exit code after completion

### Usage Example

```python
from pipeline_orchestrator import (
    ExperimentConfig,
    launch_experiment_suite,
)

# Load configuration
config = ExperimentConfig()

# Launch experiment suite
process = launch_experiment_suite(config)

print(f"Experiment suite started with PID: {process.pid}")
print(f"Monitor progress: tail -f kafka-structured/experiments/experiment_run_log.txt")

# Wait for completion (optional)
exit_code = process.wait()
print(f"Experiment suite completed with exit code: {exit_code}")
```

## Testing

### Tests Created

1. **test_launcher_manual.py**
   - Verifies function signature and imports
   - Tests log file path generation
   - Confirms `run_experiments.py` exists

2. **test_launcher_integration.py**
   - Tests command construction
   - Verifies unbuffered output flag
   - Confirms no pause flag
   - Documents process handle interface

3. **demo_launcher.py**
   - Demonstrates complete workflow
   - Shows monitoring capabilities
   - Documents key features

### Test Results

All tests passed successfully:
- ✓ Function is callable and importable
- ✓ Command construction verified
- ✓ Log file path calculation correct
- ✓ Unbuffered output requirement met
- ✓ No-pause requirement met
- ✓ Process handle interface documented

## Files Modified

1. **kafka-structured/experiments/pipeline_orchestrator.py**
   - Added `launch_experiment_suite()` function
   - Added comprehensive docstring with preconditions/postconditions
   - Implemented all requirements from design document

## Files Created

1. **kafka-structured/experiments/test_launcher_manual.py**
   - Manual tests for function verification

2. **kafka-structured/experiments/test_launcher_integration.py**
   - Integration tests for requirements verification

3. **kafka-structured/experiments/demo_launcher.py**
   - Demonstration of launcher workflow

4. **kafka-structured/experiments/TASK_3.1_IMPLEMENTATION.md**
   - This implementation summary

## Compliance with Requirements

### Design Requirements Met

✓ Uses `subprocess.Popen` for background execution
✓ Uses `python -u` flag for unbuffered output
✓ Redirects stdout/stderr to log file
✓ NO `--pause-before-start` flag passed
✓ Returns process handle for monitoring
✓ Log file created in experiments directory
✓ Supports custom log file path
✓ Error handling for missing script
✓ Creates log directory if needed

### Preconditions Satisfied

✓ Infrastructure validation should pass first (handled by orchestrator)
✓ `run_experiments.py` exists in correct location
✓ Results directory exists (created by ExperimentConfig)
✓ Python interpreter available

### Postconditions Guaranteed

✓ Returns subprocess.Popen handle
✓ Process runs with unbuffered output
✓ stdout/stderr redirected to log file
✓ NO --pause-before-start flag
✓ Process runs in background
✓ Can be monitored via process handle

## Next Steps

This function is ready to be integrated into the main pipeline orchestration workflow (Task 3.2 - Implement progress monitoring).

The process handle can be used to:
1. Monitor if the experiment is still running
2. Read the log file for progress updates
3. Wait for completion
4. Handle errors or interruptions

## Notes

- The function uses system Python (not MSYS Python) as per requirements
- Log file is line-buffered for real-time updates
- stderr is merged into stdout for unified logging
- Working directory is set to experiments directory
- Process runs independently and can be monitored asynchronously
