"""
Debug tool for PT-Gen API.
Usage: python -m src.debug_ptgen

Enter a Douban/IMDb URL and see:
  1. Raw API response JSON
  2. Generated description text
  3. Parsed metadata (area, category, etc.)
"""
import json
import sys

import pyperclip

from src.core.ptgen import get_pt_gen_description
from src.core.tool import get_settings, get_data_from_pt_gen_description


def separator(title: str = "") -> None:
    width = 80
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print(f"\n{'-' * width}")


def main():
    pt_gen_api_url = get_settings("pt_gen_api_url")
    print(f"PT-Gen API URL: {pt_gen_api_url}")
    if not pt_gen_api_url:
        print("Error: pt_gen_api_url is not configured in static/settings.json")
        sys.exit(1)

    while True:
        separator()
        url = input("Enter Douban/IMDb URL (or 'q' to quit): ").strip()
        if url.lower() in ('q', 'quit', 'exit'):
            print("Bye!")
            break
        if not url:
            continue

        print(f"\nFetching data for: {url}")
        print("Please wait...")

        success, result = get_pt_gen_description(pt_gen_api_url, url)

        if not success:
            separator("ERROR")
            print(result)
            continue

        format_data, raw_data = result

        # ── Section 1: Raw API Response ──
        separator("1. RAW API RESPONSE (JSON)")
        pretty_json = json.dumps(raw_data, indent=2, ensure_ascii=False)
        print(pretty_json)

        # ── Section 2: Generated Description ──
        separator("2. GENERATED DESCRIPTION (format_data)")
        print(format_data)

        # ── Section 3: Parsed Metadata ──
        separator("3. PARSED METADATA")
        (imdb_url, douban_url, category, area,
         video_format, audio_codec, video_codec, medium) = \
            get_data_from_pt_gen_description(
                main_title="",  # no file title in debug mode
                description=format_data,
                media_info="",
                source="",
                category=""
            )
        metadata = {
            "IMDb URL": imdb_url,
            "Douban URL": douban_url,
            "Category (类型)": category,
            "Area (地区)": area,
            "Video Format": video_format,
            "Audio Codec": audio_codec,
            "Video Codec": video_codec,
            "Medium": medium,
        }
        for k, v in metadata.items():
            print(f"  {k:20s}: {v or '(empty)'}")

        # ── Section 4: Key fields from raw data ──
        separator("4. KEY FIELDS FROM RAW DATA")
        key_fields = [
            "chinese_title", "foreign_title", "year", "category",
            "region", "genre", "language", "director", "writer",
            "cast", "episodes", "duration", "imdb_rating", "imdb_id",
            "douban_rating", "douban_id", "poster", "introduction",
        ]
        for field in key_fields:
            val = raw_data.get(field)
            if val is not None:
                # Truncate long lists/strings for readability
                val_str = json.dumps(val, ensure_ascii=False) if isinstance(val, (list, dict)) else str(val)
                if len(val_str) > 200:
                    val_str = val_str[:200] + "..."
                print(f"  {field:20s}: {val_str}")

        # ── Copy description to clipboard ──
        separator()
        try:
            pyperclip.copy(format_data)
            print("✅ Description copied to clipboard!")
        except Exception:
            print("(Could not copy to clipboard)")


if __name__ == "__main__":
    main()
