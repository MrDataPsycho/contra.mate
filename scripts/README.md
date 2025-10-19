# ContraMate Scripts

This directory contains utility scripts for managing the ContraMate data pipeline.

## Available Scripts

### `sync_data_to_s3.sh`

Sync processed data directories from local storage to AWS S3.

**What it syncs:**
- `data/bronze-v2` - Raw PDF documents
- `data/silver` - Converted markdown documents
- `data/gold` - Chunked JSON documents
- `data/platinum-cached` - Cached platinum models (Parquet with embeddings)

**S3 Destination:** `s3://sheikh-files/contra.mate/data/`

#### Prerequisites

1. **AWS CLI installed:**
   ```bash
   # macOS
   brew install awscli

   # Linux/Windows
   pip install awscli
   ```

2. **AWS credentials configured:**
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, region, and output format
   ```

3. **S3 bucket access:**
   - Ensure you have read/write permissions to `s3://sheikh-files/contra.mate/data/`

#### Usage

**Basic sync (upload only):**
```bash
./scripts/sync_data_to_s3.sh
```

**Preview changes (dry run):**
```bash
./scripts/sync_data_to_s3.sh --dry-run
```

**Sync with delete (removes files from S3 that don't exist locally):**
```bash
./scripts/sync_data_to_s3.sh --delete
```
⚠️ **Warning:** `--delete` will remove files from S3! Use with caution.

**Preview sync with delete:**
```bash
./scripts/sync_data_to_s3.sh --dry-run --delete
```

**Show help:**
```bash
./scripts/sync_data_to_s3.sh --help
```

#### Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview what would be synced without actually uploading |
| `--delete` | Delete files in S3 that don't exist locally (DESTRUCTIVE!) |
| `--help`, `-h` | Show help message |

#### How It Works

1. **Verification:**
   - Checks AWS CLI is installed
   - Verifies AWS credentials are configured
   - Confirms S3 bucket is accessible

2. **Statistics:**
   - Shows local directory sizes and file counts
   - Displays total files to sync

3. **Sync:**
   - Uses `aws s3 sync` for efficient incremental uploads
   - Only uploads changed/new files (unless `--delete` is used)
   - Shows progress for each directory

4. **Summary:**
   - Reports success/failure for each directory
   - Shows final S3 bucket contents

#### Examples

**Typical workflow:**
```bash
# 1. Preview what will be synced
./scripts/sync_data_to_s3.sh --dry-run

# 2. If looks good, sync for real
./scripts/sync_data_to_s3.sh

# 3. Verify on S3 (optional)
aws s3 ls s3://sheikh-files/contra.mate/data/ --recursive --human-readable
```

**Clean sync (mirror local to S3):**
```bash
# Preview
./scripts/sync_data_to_s3.sh --dry-run --delete

# Execute (removes files from S3 that aren't in local)
./scripts/sync_data_to_s3.sh --delete
```

#### Output Example

```
╔════════════════════════════════════════════════════════════╗
║              Data Sync to S3 Configuration                 ║
╚════════════════════════════════════════════════════════════╝

ℹ S3 Bucket:    s3://sheikh-files/contra.mate/data
ℹ Local Dir:    data
ℹ Dry Run:      No
ℹ Delete Mode:  No (upload only)

╔════════════════════════════════════════════════════════════╗
║              Local Directory Statistics                    ║
╚════════════════════════════════════════════════════════════╝

  bronze-v2            :        500 files,      250MB
  silver               :        500 files,      150MB
  gold                 :        500 files,       75MB
  platinum-cached      :        500 files,       50MB

ℹ Total files to sync: 2000

╔════════════════════════════════════════════════════════════╗
║                  Starting Sync Process                     ║
╚════════════════════════════════════════════════════════════╝

ℹ Syncing: bronze-v2
  Local:  data/bronze-v2
  S3:     s3://sheikh-files/contra.mate/data/bronze-v2/

upload: data/bronze-v2/project1/doc1.pdf to s3://...
...
✓ Completed: bronze-v2

...

╔════════════════════════════════════════════════════════════╗
║                    Sync Summary                            ║
╚════════════════════════════════════════════════════════════╝

  Successful:  4
  Failed:      0
  Skipped:     0
  Total:       4

✓ All syncs completed successfully!
```

#### Troubleshooting

**Error: AWS CLI not found**
```bash
# Install AWS CLI
brew install awscli  # macOS
pip install awscli   # Others
```

**Error: AWS credentials not configured**
```bash
# Configure credentials
aws configure
```

**Error: Cannot access S3 bucket**
- Verify bucket name is correct: `s3://sheikh-files/contra.mate/data`
- Check your AWS user has S3 read/write permissions
- Verify region matches your bucket location

**Error: Permission denied**
```bash
# Make script executable
chmod +x scripts/sync_data_to_s3.sh
```

#### Best Practices

1. **Always test with `--dry-run` first** to preview changes
2. **Backup important data** before using `--delete` flag
3. **Monitor sync progress** for large datasets
4. **Use `--delete` sparingly** - it permanently removes S3 files
5. **Verify sync** after completion using `aws s3 ls`

#### Notes

- The script uses `aws s3 sync`, which is **incremental** - only uploads changed files
- Files are compared by size and modification time
- Large files may take time to upload depending on your internet connection
- The script preserves directory structure in S3
