# update-kubeconfig

Replace `~/.kube/config` with a new kubeconfig file, creating a timestamped backup.

## Usage

```
/update-kubeconfig <path-to-new-kubeconfig>
```

**Examples:**
- `/update-kubeconfig ~/Downloads/example-context.yaml`

## What it does

Backs up `~/.kube/config` to `~/.kube/config.bkp.<YYYYMMDD-HHMMSS>` then copies
the provided file into its place. If no existing config is found, the backup step
is skipped.

```bash
python3 scripts/update_kubeconfig.py "$ARGUMENTS"
```
