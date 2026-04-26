# AGENTS.md - How to Build a HyperTTS Service

This guide explains how to create a new TTS (Text-to-Speech) or dictionary service for the HyperTTS Anki addon. If you need to examine HyperTTS source files beyond what is described here, the full codebase is available at https://github.com/Vocab-Apps/anki-hyper-tts.

## Key Source Files

| File | Purpose |
|------|---------|
| [hypertts_addon/service.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/service.py) | `ServiceBase` abstract class all services extend |
| [hypertts_addon/voice.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/voice.py) | `TtsVoice_v3` dataclass representing a voice |
| [hypertts_addon/languages.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/languages.py) | `Language` and `AudioLanguage` enums |
| [hypertts_addon/constants.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/constants.py) | `Gender`, `ServiceType`, `ServiceFee` enums |
| [hypertts_addon/errors.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/errors.py) | `ServiceRequestError` hierarchy (`PermanentError`, `TransientError`, etc.) |
| [hypertts_addon/options.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/options.py) | `AudioFormat` enum, `AUDIO_FORMAT_PARAMETER` constant |

Example services:
- [service_cambridge.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/services/service_cambridge.py) - Simple dictionary service (web scraping, no config)
- [service_googletranslate.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/services/service_googletranslate.py) - Simple free TTS service
- [service_openai.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/services/service_openai.py) - Paid API service with options

## Service Discovery

Services are auto-discovered by the `ServiceManager`. To be discovered:
1. Place your file in `services/`
2. Name it `service_<yourservice>.py`
3. Subclass `ServiceBase` — the manager finds all `ServiceBase` subclasses automatically

## ServiceBase — Required Interface

Every service must subclass `ServiceBase` and implement these:

```python
from hypertts_addon import service
from hypertts_addon import constants
from hypertts_addon import voice
from hypertts_addon import languages

class MyService(service.ServiceBase):
    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        # constants.ServiceType.tts       — generates audio for any text
        # constants.ServiceType.dictionary — looks up recordings of individual words
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        # constants.ServiceFee.free or constants.ServiceFee.paid
        return constants.ServiceFee.paid

    def voice_list(self) -> list[voice.TtsVoice_v3]:
        # Return the list of available voices (see below)
        ...

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, options) -> bytes:
        # Generate or fetch audio, return raw bytes (typically MP3)
        ...
```

### Optional Methods

```python
def configuration_options(self):
    """Declare config fields the user must fill in (API keys, regions, etc.)."""
    return {
        'api_key': str,           # text input
        'throttle_seconds': float, # numeric input
        'region': ['us-east-1', 'eu-west-1'],  # dropdown list
    }

def configure(self, config):
    """Called with the user's config dict. Validate/store values here."""
    self._config = config
    self.api_key = self.get_configuration_value_mandatory('api_key')

def enabled_by_default(self):
    """Return True if service needs no config to work (e.g. free web services)."""
    return False

def cloudlanguagetools_enabled(self):
    """Return True if this service is also available through the Cloud Language Tools proxy."""
    return False
```

### Configuration Helpers (inherited from ServiceBase)

```python
# Raises MissingServiceConfiguration if key is missing or empty string
value = self.get_configuration_value_mandatory('api_key')

# Returns default_value if key is missing
value = self.get_configuration_value_optional('throttle_seconds', 0)
```

## Building the Voice List

Each voice is a `TtsVoice_v3` instance. Do **not** use `basic_voice_list()` — build voices directly.

### TtsVoice_v3 Fields

```python
@dataclasses.dataclass
class TtsVoice_v3:
    name: str                                       # Display name shown to user
    voice_key: Dict[str, Any]                       # Service-specific identifier (dict or str)
    options: Dict[str, Dict[str, Any]]              # Adjustable parameters (see Options section)
    service: str                                    # Service name string (use self.name)
    gender: constants.Gender                        # Gender.Male, Gender.Female, or Gender.Any
    audio_languages: List[languages.AudioLanguage]  # Supported AudioLanguage values
    service_fee: constants.ServiceFee               # ServiceFee.free or ServiceFee.paid
```

### Using build_voice_v3 Helper

For single-language voices, use the `build_voice_v3` helper:

```python
from hypertts_addon import voice

voices.append(voice.build_voice_v3(
    name='English Voice',
    gender=constants.Gender.Female,
    language=languages.AudioLanguage.en_US,  # single AudioLanguage
    service=self,                            # pass the service instance
    voice_key={'name': 'my-voice-id'},       # whatever your API needs to identify the voice
    options={}                               # voice options (see Options section)
))
```

### Constructing TtsVoice_v3 Directly

For more control (e.g. multilingual voices, custom voice_key as string):

```python
voice.TtsVoice_v3(
    name='UK English',
    gender=constants.Gender.Female,
    audio_languages=[languages.AudioLanguage.en_GB],
    service=self.name,           # string, not the service object
    voice_key='uk',              # can be a simple string
    options={},
    service_fee=self.service_fee
)
```

### AudioLanguage Enum

`AudioLanguage` represents a language+region combination. Common values:

| Value | Description |
|-------|-------------|
| `AudioLanguage.en_US` | English (US) |
| `AudioLanguage.en_GB` | English (UK) |
| `AudioLanguage.fr_FR` | French (France) |
| `AudioLanguage.de_DE` | German (Germany) |
| `AudioLanguage.zh_CN` | Chinese (Mandarin, Simplified) |
| `AudioLanguage.ja_JP` | Japanese |
| `AudioLanguage.ko_KR` | Korean |
| `AudioLanguage.es_ES` | Spanish (Spain) |
| `AudioLanguage.pt_BR` | Portuguese (Brazil) |
| `AudioLanguage.it_IT` | Italian |

Each `AudioLanguage` has a `.lang` property returning the parent `Language` enum (e.g. `AudioLanguage.en_US.lang == Language.en`).

See the full list in [languages.py](https://github.com/Vocab-Apps/anki-hyper-tts/blob/main/hypertts_addon/languages.py).

## Voice Options

Options let users adjust parameters like speed, pitch, or audio format. Each option is a dict with metadata:

```python
options = {
    'speed': {
        'type': 'number',    # float slider
        'min': 0.25,
        'max': 4.0,
        'default': 1.0
    },
    'pitch': {
        'type': 'number_int', # integer slider
        'min': -20,
        'max': 20,
        'default': 0
    },
    'model': {
        'type': 'list',       # dropdown
        'values': ['standard', 'hd'],
        'default': 'standard'
    },
    'instructions': {
        'type': 'text',       # free text input
        'default': ''
    }
}
```

**Option types** (from `options.ParameterType`):
- `number` — floating point slider
- `number_int` — integer slider
- `list` — dropdown of string values
- `text` — free text input

### Audio Format Option

To support multiple output formats, include the format option:

```python
from hypertts_addon import options

format_option = {
    options.AUDIO_FORMAT_PARAMETER: {  # key is 'format'
        'type': 'list',
        'values': [e.name for e in options.AudioFormat],  # ['mp3', 'ogg_opus', 'ogg_vorbis']
        'default': 'mp3'
    }
}
```

Read it in `get_tts_audio`:

```python
audio_format_str = voice_options.get(options.AUDIO_FORMAT_PARAMETER, options.AudioFormat.mp3.name)
audio_format = options.AudioFormat[audio_format_str]
```

## Generating Audio (get_tts_audio)

```python
def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options) -> bytes:
```

- `source_text` — the text to speak
- `voice` — the `TtsVoice_v3` selected by the user; use `voice.voice_key` to identify the voice for your API
- `voice_options` — dict of user-selected option values; fall back to defaults from `voice.options`
- **Return** raw audio bytes (MP3 by default)

### Reading Options with Defaults

```python
speed = voice_options.get('speed', voice.options['speed']['default'])
```

### Error Handling

`get_tts_audio` failures must be raised as one of the exceptions in the `ServiceRequestError`
hierarchy. The retry/error-reporting layer keys off the exception class, so picking the right
one matters — it determines whether the request is retried, surfaced to the user, or counted
silently as "audio not found".

```
ServiceRequestError(source_text, voice, error_message)
├── PermanentError                  retryable = False
│   ├── ServicePermissionError      auth/authorization failure (401, 403)
│   ├── ServiceInputError           input the service can't handle (unsupported format,
│   │                                empty-after-tokenization, text too long, etc.)
│   ├── AudioNotFoundError          dictionary lookup found no recording for this word/voice
│   └── AudioNotFoundAnyVoiceError  internal — raised by the priority-mode runner, not by
│                                    individual services
└── TransientError                  retryable = True
    ├── RateLimitError              generic 429 with no Retry-After
    ├── RateLimitRetryAfterError    429 with a Retry-After value (pass it as 4th arg)
    ├── ServiceTimeoutError         HTTP request timed out
    ├── ServiceConnectionError      DNS failure, connection refused, network unreachable
    └── UnknownServiceError         unclassified upstream failure
```

`RequestError` also exists as a legacy catch-all. Prefer one of the typed subclasses above
for new code so retry logic works correctly; only fall back to `RequestError` when the failure
genuinely doesn't fit any category.

#### When to raise what

| Situation | Exception |
|-----------|-----------|
| HTTP 401 / 403, invalid API key, expired token | `ServicePermissionError` |
| HTTP 429 with `Retry-After` header | `RateLimitRetryAfterError(..., retry_after)` |
| HTTP 429 without `Retry-After` | `RateLimitError` |
| `requests.Timeout` / `socket.timeout` | `ServiceTimeoutError` |
| `requests.ConnectionError`, DNS failure, refused | `ServiceConnectionError` |
| Service rejects the input (format not supported, text too long, tokenizer produced empty input) | `ServiceInputError` |
| Dictionary service: no recording for this word | `AudioNotFoundError` |
| Other 4xx that won't succeed on retry | `PermanentError` (or a more specific subclass) |
| Other 5xx / unexpected upstream failure that may succeed on retry | `UnknownServiceError` |
| Truly ambiguous — can't classify | `RequestError` (legacy fallback) |

#### Examples

```python
from hypertts_addon import errors

# Auth failure — won't succeed on retry, surfaces to the user
if response.status_code == 401:
    raise errors.ServicePermissionError(source_text, voice, f'auth failed: {response.text}')

# Rate limited with a Retry-After header — retried after the given delay
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 30))
    raise errors.RateLimitRetryAfterError(source_text, voice, response.text, retry_after)

# Service can't process this specific input — permanent for this text, not the service
if audio_format != options.AudioFormat.mp3:
    raise errors.ServiceInputError(source_text, voice,
        f'{self.name} only supports mp3; {audio_format.name} not supported')

# Dictionary service — word not in the dictionary
raise errors.AudioNotFoundError(source_text, voice)

# Wrap network-layer exceptions
try:
    response = requests.post(url, json=data, timeout=constants.RequestTimeout)
except requests.exceptions.Timeout as e:
    raise errors.ServiceTimeoutError(source_text, voice, str(e)) from e
except requests.exceptions.ConnectionError as e:
    raise errors.ServiceConnectionError(source_text, voice, str(e)) from e
```

#### Configuration errors

Don't raise these yourself — they come from the `ServiceBase` helpers:

- `MissingServiceConfiguration` is raised automatically by `get_configuration_value_mandatory`
  when the user hasn't set a required key (e.g. an API key). Just call the helper; don't
  pre-check.

## Complete Example: TTS Service with API Key

```python
import requests
from typing import List

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)


class ExampleTTS(service.ServiceBase):
    CONFIG_API_KEY = 'api_key'

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.tts

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.paid

    def configuration_options(self):
        return {
            self.CONFIG_API_KEY: str
        }

    def voice_list(self) -> List[voice.TtsVoice_v3]:
        voice_options = {
            'speed': {
                'type': 'number',
                'min': 0.5,
                'max': 2.0,
                'default': 1.0
            }
        }
        return [
            voice.TtsVoice_v3(
                name='Alice',
                gender=constants.Gender.Female,
                audio_languages=[languages.AudioLanguage.en_US],
                service=self.name,
                voice_key={'name': 'alice'},
                options=voice_options,
                service_fee=self.service_fee
            ),
            voice.TtsVoice_v3(
                name='Bob',
                gender=constants.Gender.Male,
                audio_languages=[languages.AudioLanguage.en_US, languages.AudioLanguage.en_GB],
                service=self.name,
                voice_key={'name': 'bob'},
                options=voice_options,
                service_fee=self.service_fee
            ),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)

        speed = voice_options.get('speed', voice.options['speed']['default'])

        try:
            response = requests.post(
                'https://api.example.com/v1/tts',
                json={
                    'text': source_text,
                    'voice': voice.voice_key['name'],
                    'speed': speed,
                },
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=30,
            )
        except requests.exceptions.Timeout as e:
            raise errors.ServiceTimeoutError(source_text, voice, str(e)) from e
        except requests.exceptions.ConnectionError as e:
            raise errors.ServiceConnectionError(source_text, voice, str(e)) from e

        if response.status_code in (401, 403):
            raise errors.ServicePermissionError(source_text, voice, f'auth failed: {response.text}')
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 30))
            raise errors.RateLimitRetryAfterError(source_text, voice, response.text, retry_after)
        if response.status_code != 200:
            raise errors.UnknownServiceError(source_text, voice, f'HTTP {response.status_code}: {response.text}')

        return response.content
```

## Complete Example: Dictionary Service (Web Scraping)

```python
import requests
import bs4

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)


class ExampleDictionary(service.ServiceBase):

    def __init__(self):
        service.ServiceBase.__init__(self)

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def enabled_by_default(self):
        return True

    def voice_list(self):
        return [
            voice.TtsVoice_v3(
                name='US English',
                gender=constants.Gender.Any,
                audio_languages=[languages.AudioLanguage.en_US],
                service=self.name,
                voice_key='us',
                options={},
                service_fee=self.service_fee
            ),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }

        response = requests.get(f'https://dictionary.example.com/{source_text}', headers=headers)
        soup = bs4.BeautifulSoup(response.content, 'html.parser')

        audio_tag = soup.find('source', {'type': 'audio/mpeg'})
        if audio_tag and audio_tag.get('src'):
            audio_response = requests.get(audio_tag['src'], headers=headers)
            return audio_response.content

        raise errors.AudioNotFoundError(source_text, voice)
```

