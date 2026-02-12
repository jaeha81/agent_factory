## Next
- Implement "agent create" for non-master IDs via CLI args (e.g., create_worker.py or create_master.py --id A0002)
- Add preflight check: if logs/*.log is directory -> auto-fix (optional, keep safe_e2e as external guard)
- Add CI smoke: run create_master.py in clean env (no deletion of existing agents), verify logs append + registry update
