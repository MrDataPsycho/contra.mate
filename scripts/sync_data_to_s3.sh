#!/bin/bash
#
# sync_data_to_s3.sh
# Sync processed data from local to S3 bucket
#
# This script syncs the following data directories to S3:
# - data/bronze-v2    : Raw PDF documents
# - data/silver       : Converted markdown documents
# - data/gold         : Chunked JSON documents
# - data/platinum-cached : Cached platinum models (Parquet with embeddings)
#
# S3 Bucket: s3://sheikh-files/contra.mate/data/
#
# Usage:
#   ./scripts/sync_data_to_s3.sh [--dry-run] [--delete] [--help]
#
# Options:
#   --dry-run    : Preview what would be synced without actually syncing
#   --delete     : Delete files in S3 that don't exist locally (use with caution!)
#   --help       : Show this help message
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
S3_BUCKET="s3://sheikh-files/contra.mate/data"
LOCAL_DATA_DIR="data"

# Directories to sync
DIRS_TO_SYNC=(
    "bronze-v2"
    "silver"
    "gold"
    "platinum-cached"
)

# Parse command line arguments
DRY_RUN=""
DELETE_FLAG=""
SHOW_HELP=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN="--dryrun"
            shift
            ;;
        --delete)
            DELETE_FLAG="--delete"
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            SHOW_HELP=true
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Sync processed data directories to S3."
    echo ""
    echo "Options:"
    echo "  --dry-run    Preview what would be synced without actually syncing"
    echo "  --delete     Delete files in S3 that don't exist locally (DESTRUCTIVE!)"
    echo "  --help, -h   Show this help message"
    echo ""
    echo "Directories synced:"
    for dir in "${DIRS_TO_SYNC[@]}"; do
        echo "  - data/$dir"
    done
    echo ""
    echo "S3 Destination: $S3_BUCKET"
    echo ""
    echo "Examples:"
    echo "  $0                      # Normal sync (upload only)"
    echo "  $0 --dry-run            # Preview changes"
    echo "  $0 --delete             # Sync and delete removed files"
    echo "  $0 --dry-run --delete   # Preview sync with delete"
    exit 0
fi

# Function to print colored messages
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first:"
    echo "  brew install awscli  # macOS"
    echo "  pip install awscli   # Linux/Windows"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured or invalid."
    log_info "Configure with: aws configure"
    exit 1
fi

log_success "AWS CLI configured"

# Verify S3 bucket exists and is accessible
# Extract bucket name from S3 path (e.g., s3://bucket-name/path -> bucket-name)
S3_BUCKET_NAME=$(echo "$S3_BUCKET" | sed 's|s3://||' | cut -d'/' -f1)
log_info "Verifying S3 bucket access: $S3_BUCKET"

# First check if bucket itself is accessible
if ! aws s3 ls "s3://$S3_BUCKET_NAME" &> /dev/null; then
    log_error "Cannot access S3 bucket: s3://$S3_BUCKET_NAME"
    log_info "Please verify:"
    log_info "  1. Bucket exists"
    log_info "  2. AWS credentials have proper permissions"
    exit 1
fi

# Then verify the specific S3 path/prefix exists or can be created
# Use || true to allow non-existent paths (they'll be created during sync)
aws s3 ls "$S3_BUCKET/" &> /dev/null || log_info "S3 path will be created: $S3_BUCKET/"

log_success "S3 bucket accessible"

# Check if data directory exists
if [ ! -d "$LOCAL_DATA_DIR" ]; then
    log_error "Local data directory not found: $LOCAL_DATA_DIR"
    exit 1
fi

# Display sync configuration
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Data Sync to S3 Configuration                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
log_info "S3 Bucket:    $S3_BUCKET"
log_info "Local Dir:    $LOCAL_DATA_DIR"
log_info "Dry Run:      ${DRY_RUN:-No}"
log_info "Delete Mode:  ${DELETE_FLAG:-No (upload only)}"
echo ""

# Warn about delete mode
if [ -n "$DELETE_FLAG" ]; then
    log_warning "DELETE MODE ENABLED!"
    log_warning "Files in S3 that don't exist locally will be DELETED!"
    if [ -z "$DRY_RUN" ]; then
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "Sync cancelled by user"
            exit 0
        fi
    fi
fi

# Function to get directory size
get_dir_size() {
    local dir=$1
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | awk '{print $1}'
    else
        echo "N/A"
    fi
}

# Function to count files in directory
count_files() {
    local dir=$1
    if [ -d "$dir" ]; then
        find "$dir" -type f | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# Show directory statistics
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Local Directory Statistics                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

total_files=0
for dir in "${DIRS_TO_SYNC[@]}"; do
    local_path="$LOCAL_DATA_DIR/$dir"
    if [ -d "$local_path" ]; then
        size=$(get_dir_size "$local_path")
        files=$(count_files "$local_path")
        total_files=$((total_files + files))
        printf "  %-20s : %10s files, %10s\n" "$dir" "$files" "$size"
    else
        log_warning "Directory not found: $local_path (skipping)"
    fi
done

echo ""
log_info "Total files to sync: $total_files"
echo ""

# Confirm before proceeding (unless dry run)
if [ -z "$DRY_RUN" ]; then
    read -p "Proceed with sync? (yes/no): " proceed
    if [ "$proceed" != "yes" ]; then
        log_info "Sync cancelled by user"
        exit 0
    fi
    echo ""
fi

# Start sync
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Starting Sync Process                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Track sync statistics
sync_success=0
sync_failed=0
sync_skipped=0

# Sync each directory
for dir in "${DIRS_TO_SYNC[@]}"; do
    local_path="$LOCAL_DATA_DIR/$dir"
    s3_path="$S3_BUCKET/$dir/"

    if [ ! -d "$local_path" ]; then
        log_warning "Skipping $dir (directory not found)"
        sync_skipped=$((sync_skipped + 1))
        continue
    fi

    log_info "Syncing: $dir"
    echo "  Local:  $local_path"
    echo "  S3:     $s3_path"
    echo ""

    # Build aws s3 sync command
    sync_cmd="aws s3 sync \"$local_path\" \"$s3_path\""

    # Add flags
    if [ -n "$DRY_RUN" ]; then
        sync_cmd="$sync_cmd $DRY_RUN"
    fi

    if [ -n "$DELETE_FLAG" ]; then
        sync_cmd="$sync_cmd $DELETE_FLAG"
    fi

    # Execute sync
    if eval $sync_cmd; then
        log_success "Completed: $dir"
        sync_success=$((sync_success + 1))
    else
        log_error "Failed: $dir"
        sync_failed=$((sync_failed + 1))
    fi

    echo ""
done

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Sync Summary                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ -n "$DRY_RUN" ]; then
    log_info "DRY RUN - No actual changes made"
fi

echo "  Successful:  $sync_success"
echo "  Failed:      $sync_failed"
echo "  Skipped:     $sync_skipped"
echo "  Total:       ${#DIRS_TO_SYNC[@]}"
echo ""

if [ $sync_failed -eq 0 ]; then
    log_success "All syncs completed successfully!"
else
    log_error "Some syncs failed. Please check the errors above."
    exit 1
fi

# Show S3 bucket contents
if [ -z "$DRY_RUN" ]; then
    echo ""
    log_info "Verifying S3 bucket contents..."
    echo ""
    aws s3 ls "$S3_BUCKET/" --human-readable --summarize
fi

echo ""
log_success "Sync process complete!"
