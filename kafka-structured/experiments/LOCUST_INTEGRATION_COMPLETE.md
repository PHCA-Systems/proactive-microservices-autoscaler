# Locust VM Integration - COMPLETE

## Summary

Integrated remote Locust load generator (running on GCP VM `locust-runner`) with the experiment runner.

## Configuration

The experiment runner now connects to your existing Locust VM via SSH to trigger load tests.

### Default Configuration

```python
LOCUST_VM_IP = "136.115.51.98"
LOCUST_SSH_USER = "User"
LOCUST_SSH_KEY = "~/.ssh/google_compute_engine"
SOCK_SHOP_EXTERNAL_IP = "104.154.246.88"
```

### Environment Variables (Optional Overrides)

You can override these defaults using environment variables:

```bash
export LOCUST_VM_IP="your-vm-ip"
export LOCUST_SSH_USER="your-username"
export LOCUST_SSH_KEY="/path/to/your/ssh/key"
export SOCK_SHOP_EXTERNAL_IP="your-sock-shop-ip"
```

## Implementation Details

### Functions Added

1. **`start_locust(pattern, duration_min)`**
   - Starts Locust on remote VM via SSH
   - Sets `LOCUST_RUN_TIME_MINUTES` environment variable for LoadTestShape
   - Uses pattern-specific locustfile: `locustfile_{pattern}.py`
   - Runs in headless mode for specified duration
   - Returns subprocess handle for monitoring

2. **`stop_locust(proc)`**
   - Gracefully terminates Locust process
   - Waits up to 30 seconds for clean shutdown
   - Force kills if necessary

### SSH Command Structure

```bash
ssh -i ~/.ssh/google_compute_engine \
    -o StrictHostKeyChecking=no \
    -o BatchMode=yes \
    User@136.115.51.98 \
    "source ~/locust-venv/bin/activate && \
     LOCUST_RUN_TIME_MINUTES=12 \
     locust -f ~/locustfile_constant.py --headless --run-time 12m \
     --host http://104.154.246.88 2>&1"
```

### Load Patterns

The experiment runner uses 4 load patterns, each with its own locustfile on the VM:

| Pattern  | Locustfile                | Description                    |
|----------|---------------------------|--------------------------------|
| constant | locustfile_constant.py    | Steady load                    |
| step     | locustfile_step.py        | Step increases                 |
| spike    | locustfile_spike.py       | Sudden load spikes             |
| ramp     | locustfile_ramp.py        | Gradual load increase          |

## Validation

Added validation check in `main()` to verify Locust VM connectivity before starting experiments:

```
Checking Locust VM connectivity...
  ✓ Locust VM accessible at 136.115.51.98
```

The validation:
- Tests SSH connection to the VM
- Uses 5-second connection timeout
- Fails fast if VM is unreachable
- Prevents experiment from starting if VM is down

## Experiment Flow

For each experimental run:

1. **Enable condition** (proactive or reactive)
2. **Reset cluster** (all services to 1 replica)
3. **Start Locust** on remote VM (12 minutes)
4. **Collect metrics** every 30 seconds (24 intervals)
5. **Stop Locust** gracefully
6. **Settle** for 3 minutes
7. **Write results** to JSONL file

Total per run: ~15 minutes (12 min load + 3 min settle)

## Prerequisites on Locust VM

The VM should already have (from previous setup):

1. **Python virtual environment**: `~/locust-venv`
2. **Locust installed**: In the venv
3. **Locustfiles**: `~/locustfile_{constant,step,spike,ramp}.py`
4. **SSH access**: Key-based authentication configured

## Testing

### Test SSH Connectivity

```bash
ssh -i ~/.ssh/google_compute_engine User@136.115.51.98 "echo 'OK'"
```

Expected output: `OK`

### Test Locust Manually

```bash
ssh -i ~/.ssh/google_compute_engine User@136.115.51.98 \
  "source ~/locust-venv/bin/activate && \
   locust -f ~/locustfile_constant.py --headless --run-time 1m \
   --host http://104.154.246.88"
```

### Test Experiment Runner Validation

```bash
cd kafka-structured/experiments
python run_experiments.py --pause-before-start
```

This will run all validation checks including Locust VM connectivity.

## Troubleshooting

### SSH Connection Fails

**Problem**: `Cannot reach Locust VM: ...`

**Solutions**:
1. Verify VM is running: `gcloud compute instances list --filter="name=locust-runner"`
2. Check SSH key exists: `ls ~/.ssh/google_compute_engine`
3. Test manual SSH: `gcloud compute ssh locust-runner --zone=us-central1-a`
4. Verify firewall allows SSH (port 22)

### Locust Not Found

**Problem**: `locust: command not found`

**Solution**: SSH to VM and verify:
```bash
gcloud compute ssh locust-runner --zone=us-central1-a
source ~/locust-venv/bin/activate
which locust
```

### Locustfile Not Found

**Problem**: `No such file or directory: locustfile_*.py`

**Solution**: Verify locustfiles exist on VM:
```bash
gcloud compute ssh locust-runner --zone=us-central1-a --command="ls ~/*.py"
```

Expected output:
```
locustfile_constant.py
locustfile_ramp.py
locustfile_spike.py
locustfile_step.py
```

### Wrong Sock Shop IP

**Problem**: Locust cannot reach Sock Shop

**Solution**: Get current external IP:
```bash
kubectl get svc front-end -n sock-shop -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Update environment variable:
```bash
export SOCK_SHOP_EXTERNAL_IP="<new-ip>"
```

## Integration with Experiment Runner

The Locust integration is now fully integrated into `run_experiments.py`:

- ✅ Automatic SSH connection to VM
- ✅ Pattern-specific locustfile selection
- ✅ Duration control (12 minutes per run)
- ✅ Graceful start/stop
- ✅ Error handling
- ✅ Validation checks

## Next Steps

You can now proceed with:
1. Running validation: `python run_experiments.py --pause-before-start`
2. Deploying remaining system components to GKE (Tasks 10.1-10.4)
3. Running smoke tests (Tasks 11.1-11.4)
4. Executing the full 34-run experiment suite (Task 14)

## Notes

- The Locust VM runs independently - it doesn't need to be in the same VPC as GKE
- Load is sent to the Sock Shop external LoadBalancer IP
- SSH uses BatchMode (no interactive prompts) for automation
- Locust output is captured but not displayed (runs in background)
- Each run is isolated - Locust is started fresh for each experiment

