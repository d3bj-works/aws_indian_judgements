import os
import glob
import json
import time
from datetime import datetime

def analyze_latest_metrics():
    # Find active or latest metrics file
    metric_files = glob.glob("output*/**/metrics_*.jsonl", recursive=True)
    if not metric_files:
        print("No metrics files found.")
        return

    # Pick file with largest size / recent mtime
    target_file = sorted(metric_files, key=lambda f: os.path.getsize(f), reverse=True)[0]
    print(f"Analyzing metrics file: {target_file}")
    
    records = []
    with open(target_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    if not records:
        print("No valid records found in metrics file.")
        return

    print(f"Total processed documents in log: {len(records)}")

    # Sort by timestamp
    records.sort(key=lambda r: r.get("timestamp", 0))

    start_ts = records[0]["timestamp"]
    end_ts = records[-1]["timestamp"]
    total_elapsed_sec = max(0.001, end_ts - start_ts)

    # 1. Overall Pipeline Statistics
    total_pages = sum(r.get("pages", 0) for r in records)
    total_words = sum(r.get("word_count", 0) for r in records)
    
    avg_download_ms = sum(r.get("download_ms", 0) for r in records) / len(records)
    avg_validation_ms = sum(r.get("validation_ms", 0) for r in records) / len(records)
    avg_extract_ms = sum(r.get("extract_ms", 0) for r in records) / len(records)
    avg_clean_ms = sum(r.get("clean_ms", 0) for r in records) / len(records)
    avg_metadata_ms = sum(r.get("metadata_ms", 0) for r in records) / len(records)
    avg_entity_ms = sum(r.get("entity_ms", 0) for r in records) / len(records)
    avg_total_ms = sum(r.get("total_ms", 0) for r in records) / len(records)

    # 2. Time Window Bucket Analysis (1-minute buckets)
    bucket_size_sec = 60.0
    num_buckets = int((end_ts - start_ts) // bucket_size_sec) + 1
    
    time_series = []
    for i in range(num_buckets):
        b_start = start_ts + i * bucket_size_sec
        b_end = b_start + bucket_size_sec
        b_recs = [r for r in records if b_start <= r["timestamp"] < b_end]
        
        if b_recs:
            docs_count = len(b_recs)
            pages_count = sum(r.get("pages", 0) for r in b_recs)
            words_count = sum(r.get("word_count", 0) for r in b_recs)
            avg_duration_ms = sum(r.get("total_ms", 0) for r in b_recs) / docs_count
            avg_download = sum(r.get("download_ms", 0) for r in b_recs) / docs_count
            avg_entity = sum(r.get("entity_ms", 0) for r in b_recs) / docs_count
            avg_pages = pages_count / docs_count
            
            time_series.append({
                "minute": i + 1,
                "timestamp_sec": round(b_start - start_ts, 1),
                "docs_per_min": docs_count,
                "docs_per_sec": round(docs_count / bucket_size_sec, 2),
                "pages_per_min": pages_count,
                "avg_doc_pages": round(avg_pages, 1),
                "avg_total_ms": round(avg_duration_ms, 2),
                "avg_download_ms": round(avg_download, 2),
                "avg_entity_ms": round(avg_entity, 2)
            })

    # Try creating plot with matplotlib if available
    plot_path = None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
        
        minutes = [t["minute"] for t in time_series]
        t_sec = [t["timestamp_sec"] for t in time_series]
        t_rate = [t["docs_per_sec"] for t in time_series]
        avg_pages = [t["avg_doc_pages"] for t in time_series]
        download_times = [t["avg_download_ms"] for t in time_series]
        entity_times = [t["avg_entity_ms"] for t in time_series]
        
        # Subplot 1: Throughput Rate (PDFs/sec) over Time
        ax1.plot(t_sec, t_rate, color='#1f77b4', linewidth=2, marker='o', label='Throughput (PDFs/sec)')
        ax1.set_ylabel('PDFs / second', fontsize=11, color='#1f77b4')
        ax1.set_title('Pipeline Execution Throughput Analysis Over Time', fontsize=14, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='upper left')
        
        # Subplot 2: Document Complexity (Average Pages per Doc) over Time
        ax2.plot(t_sec, avg_pages, color='#ff7f0e', linewidth=2, marker='s', label='Avg Pages per Doc')
        ax2.set_ylabel('Pages / PDF', fontsize=11, color='#ff7f0e')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper left')
        
        # Subplot 3: Bottleneck Stage Times (Download vs Entity Extraction) over Time
        ax3.plot(t_sec, download_times, color='#2ca02c', linewidth=2, linestyle='--', label='Avg Download (ms)')
        ax3.plot(t_sec, entity_times, color='#d62728', linewidth=2, label='Avg Entity Extraction (ms)')
        ax3.set_xlabel('Elapsed Time (seconds)', fontsize=11)
        ax3.set_ylabel('Duration (ms)', fontsize=11)
        ax3.grid(True, linestyle='--', alpha=0.5)
        ax3.legend(loc='upper left')
        
        plt.tight_layout()
        
        # Save to conversation brain artifacts path
        artifacts_dir = "/home/duttadev/.gemini/antigravity-ide/brain/c8a4baee-7873-435a-802b-ea450f63f3ef"
        os.makedirs(artifacts_dir, exist_ok=True)
        plot_path = os.path.join(artifacts_dir, "throughput_analysis.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Plot successfully saved to: {plot_path}")
    except Exception as e:
        print(f"Could not render matplotlib plot: {e}")

    # Output detailed report dictionary
    analysis_report = {
        "metrics_file": target_file,
        "total_documents": len(records),
        "total_pages": total_pages,
        "total_words": total_words,
        "elapsed_time_sec": round(total_elapsed_sec, 2),
        "overall_throughput_pdfs_per_sec": round(len(records) / total_elapsed_sec, 2),
        "overall_throughput_pdfs_per_min": round((len(records) / total_elapsed_sec) * 60, 1),
        "overall_throughput_pages_per_sec": round(total_pages / total_elapsed_sec, 2),
        "stage_breakdown_avg_ms": {
            "download_ms": round(avg_download_ms, 2),
            "validation_ms": round(avg_validation_ms, 2),
            "extract_ms": round(avg_extract_ms, 2),
            "clean_ms": round(avg_clean_ms, 2),
            "metadata_ms": round(avg_metadata_ms, 2),
            "entity_ms": round(avg_entity_ms, 2),
            "total_ms": round(avg_total_ms, 2)
        },
        "stage_percentage": {
            "download_pct": round((avg_download_ms / max(0.001, avg_total_ms)) * 100, 1),
            "extract_pct": round((avg_extract_ms / max(0.001, avg_total_ms)) * 100, 1),
            "clean_pct": round((avg_clean_ms / max(0.001, avg_total_ms)) * 100, 1),
            "metadata_pct": round((avg_metadata_ms / max(0.001, avg_total_ms)) * 100, 1),
            "entity_pct": round((avg_entity_ms / max(0.001, avg_total_ms)) * 100, 1)
        },
        "plot_path": plot_path,
        "time_series_sample": time_series[:15]
    }
    
    report_json_path = os.path.join(os.path.dirname(target_file), "throughput_analysis.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(analysis_report, f, indent=2)
    print(f"Analysis saved to JSON: {report_json_path}")
    return analysis_report

if __name__ == "__main__":
    analyze_latest_metrics()
