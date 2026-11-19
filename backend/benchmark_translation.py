import asyncio
import csv
import json
import sys

from datetime import datetime
from pathlib import Path
from time import perf_counter


# -----------------------------------------
# 1. Project paths
# -----------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

TEST_FILE = (
    PROJECT_DIR / "tests"
    / "translation" / "test_cases.json"
)

RESULT_DIR = (
    PROJECT_DIR / "tests"
    / "translation" / "results"
)

RESULT_DIR.mkdir(parents=True, exist_ok=True)

# Import existing URCT translation system
sys.path.insert(0, str(BACKEND_DIR))

from app.translation import translation_service


# -----------------------------------------
# 2. Benchmark
# -----------------------------------------

async def run_benchmark():

    with TEST_FILE.open("r", encoding="utf-8") as f:
        test_cases = json.load(f)

    provider = translation_service.active_provider

    print("=" * 55)
    print("URCT TRANSLATION BENCHMARK")
    print("Provider:", provider)
    print("Total test cases:", len(test_cases))
    print("=" * 55)

    results = []

    for case in test_cases:

        print(f"\nTest {case['id']}")
        print("Category:", case["category"])
        print("Original:", case["text"])

        started = perf_counter()

        try:
            response = await translation_service.translate(
                text=case["text"],
                source_language=case["source_language"],
                target_language=case["target_language"]
            )

            elapsed = perf_counter() - started

            translated = response.translated_text or ""
            success = response.translation_success
            error = ""

        except Exception as exc:
            elapsed = perf_counter() - started
            translated = ""
            success = False
            error = str(exc)

        print("Translation:", translated)
        print("Reference:", case["reference"])
        print(f"Time: {elapsed:.3f} seconds")
        print("Success:", success)

        if error:
            print("Error:", error)

        results.append({
            "id": case["id"],
            "category": case["category"],
            "source_language": case["source_language"],
            "target_language": case["target_language"],
            "original": case["text"],
            "translation": translated,
            "reference": case["reference"],
            "time_seconds": round(elapsed, 3),
            "success": success,
            "error": error,
            "provider": provider
        })

    # -------------------------------------
    # 3. Save results
    # -------------------------------------

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        RESULT_DIR / f"benchmark_{provider}_{timestamp}.csv"
    )

    with output_file.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(results[0].keys())
        )

        writer.writeheader()
        writer.writerows(results)

    successful = [
        r for r in results if r["success"]
    ]

    print("\n" + "=" * 55)
    print("BENCHMARK SUMMARY")
    print("=" * 55)

    print("Total:", len(results))
    print("Successful:", len(successful))
    print("Failed:", len(results) - len(successful))

    if successful:
        average = sum(
            r["time_seconds"] for r in successful
        ) / len(successful)

        print(f"Average successful time: {average:.3f}s")

    print("Saved:", output_file)


if __name__ == "__main__":
    asyncio.run(run_benchmark())