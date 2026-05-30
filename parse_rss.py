#!/usr/bin/env python3
"""
parse_rss.py — fetch a podcast RSS feed and return the latest 10 episodes as JSON

Usage:
    python3 parse_rss.py <rss_url>

Output: JSON array, each item has:
    index, title, iso_date, published_date, duration, audio_url, slug
"""
import sys
import json
import urllib.request
import xml.etree.ElementTree as ET


def parse_duration(duration_str):
    if not duration_str:
        return "Unknown"
    parts = duration_str.strip().split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{h}h {m}m" if h > 0 else f"{m}m"
        elif len(parts) == 2:
            m, s = int(parts[0]), int(parts[1])
            return f"{m}m"
        else:
            total_sec = int(parts[0])
            h, rem = divmod(total_sec, 3600)
            m = rem // 60
            return f"{h}h {m}m" if h > 0 else f"{m}m"
    except (ValueError, IndexError):
        return duration_str


def slugify(text, max_len=60):
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text[:max_len]


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <rss_url>", file=sys.stderr)
        sys.exit(1)

    rss_url = sys.argv[1]
    namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}

    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    channel = root.find('channel')

    episodes = []
    for i, item in enumerate(channel.findall('item')):
        if i >= 10:
            break

        title = item.findtext('title', '').strip()
        pub_date = item.findtext('pubDate', '').strip()

        iso_date = ''
        display_date = pub_date
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            iso_date = dt.strftime('%Y-%m-%d')
            display_date = dt.strftime('%b %d, %Y')
        except Exception:
            pass

        duration = item.findtext('itunes:duration', '', namespaces).strip()
        duration = parse_duration(duration)

        audio_url = ''
        enclosure = item.find('enclosure')
        if enclosure is not None:
            audio_url = enclosure.get('url', '')

        episodes.append({
            'index': i + 1,
            'title': title,
            'iso_date': iso_date,
            'published_date': display_date,
            'duration': duration,
            'audio_url': audio_url,
            'slug': slugify(title),
        })

    print(json.dumps(episodes, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
