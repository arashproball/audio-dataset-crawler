# Data Dictionary

## Audio Dataset

The dataset contains audio-content records collected from supported
audio-content websites.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | bigint | No | Internal database identifier. |
| `source` | string | No | Source website of the audio item. |
| `content_id` | integer | Yes | Source website content identifier, when available. |
| `title` | string | Yes | Main title of the content page. |
| `content_url` | string | No | URL of the source content page. |
| `audio_url` | string | No | URL of the audio file. |
| `published_at` | string | Yes | Normalized publication date of the content. |
| `tags` | array[string] | Yes | Tags associated with the content. |
| `crawled_at` | datetime | No | Timestamp when the item was collected by the crawler. |
| `image_url` | string | Yes | URL of the image associated with the content. |
| `speaker` | string | Yes | Speaker or presenter associated with the audio item, when available. |
| `audio_title` | string | Yes | Title associated specifically with the audio item. |

## Deduplication

Audio items are uniquely identified by the combination of:

`source + audio_url`

This constraint prevents duplicate audio records from being stored
for the same source.