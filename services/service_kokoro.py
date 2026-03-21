import requests
import time
from typing import List

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages
from hypertts_addon import logging_utils

logger = logging_utils.get_child_logger(__name__)


# Voice definitions: (voice_key, display_name, gender, audio_languages)
KOKORO_VOICES = [
    # American Female voices
    ('af', 'American Female (Default)', constants.Gender.Female, [languages.AudioLanguage.en_US]),
    ('af_bella', 'Bella (American Female)', constants.Gender.Female, [languages.AudioLanguage.en_US]),
    ('af_sarah', 'Sarah (American Female)', constants.Gender.Female, [languages.AudioLanguage.en_US]),
    ('af_nicole', 'Nicole (American Female)', constants.Gender.Female, [languages.AudioLanguage.en_US]),
    ('af_sky', 'Sky (American Female)', constants.Gender.Female, [languages.AudioLanguage.en_US]),
    # American Male voices
    ('am_adam', 'Adam (American Male)', constants.Gender.Male, [languages.AudioLanguage.en_US]),
    ('am_michael', 'Michael (American Male)', constants.Gender.Male, [languages.AudioLanguage.en_US]),
    # British Female voices
    ('bf_emma', 'Emma (British Female)', constants.Gender.Female, [languages.AudioLanguage.en_GB]),
    ('bf_isabella', 'Isabella (British Female)', constants.Gender.Female, [languages.AudioLanguage.en_GB]),
    # British Male voices
    ('bm_george', 'George (British Male)', constants.Gender.Male, [languages.AudioLanguage.en_GB]),
    ('bm_lewis', 'Lewis (British Male)', constants.Gender.Male, [languages.AudioLanguage.en_GB]),
]

REPLICATE_PREDICTIONS_URL = 'https://api.replicate.com/v1/predictions'
REPLICATE_MODEL_VERSION = 'f559560eb822dc509045f3921a1921234918b91739db4bf3daab2169b71c7a13'


class Kokoro(service.ServiceBase):
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
            self.CONFIG_API_KEY: str,
        }

    def voice_list(self) -> List[voice.TtsVoice_v3]:
        voice_options = {
            'speed': {
                'type': 'number',
                'min': 0.1,
                'max': 5.0,
                'default': 1.0,
            },
        }

        voices = []
        for vkey, vname, vgender, vlanguages in KOKORO_VOICES:
            voices.append(
                voice.TtsVoice_v3(
                    name=vname,
                    gender=vgender,
                    audio_languages=vlanguages,
                    service=self.name,
                    voice_key=vkey,
                    options=voice_options,
                    service_fee=self.service_fee,
                )
            )
        return voices

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options) -> bytes:
        api_key = self.get_configuration_value_mandatory(self.CONFIG_API_KEY)
        speed = voice_options.get('speed', voice.options['speed']['default'])

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'wait',
        }
        payload = {
            'version': REPLICATE_MODEL_VERSION,
            'input': {
                'text': source_text,
                'voice': voice.voice_key,
                'speed': speed,
            }
        }

        try:
            response = requests.post(
                REPLICATE_PREDICTIONS_URL,
                json=payload,
                headers=headers,
                timeout=120,
            )
        except requests.exceptions.Timeout:
            raise errors.RequestError(source_text, voice, 'Request to Replicate timed out')

        if response.status_code not in (200, 201):
            raise errors.RequestError(
                source_text, voice,
                f'Replicate API error HTTP {response.status_code}: {response.text}'
            )

        result = response.json()
        status = result.get('status', '')

        # If the sync header didn't fully resolve, poll for completion
        if status not in ('succeeded', 'failed', 'canceled'):
            result = self._poll_prediction(api_key, result)
            status = result.get('status', '')

        if status == 'failed':
            error_msg = result.get('error', 'Unknown error')
            raise errors.RequestError(source_text, voice, f'Replicate prediction failed: {error_msg}')

        if status == 'canceled':
            raise errors.RequestError(source_text, voice, 'Replicate prediction was canceled')

        output = result.get('output')
        if not output:
            raise errors.RequestError(source_text, voice, 'No audio output returned from Replicate')

        # output is a URL to the generated audio file
        audio_url = output
        try:
            audio_response = requests.get(audio_url, timeout=60)
        except requests.exceptions.Timeout:
            raise errors.RequestError(source_text, voice, 'Timed out downloading audio from Replicate')

        if audio_response.status_code != 200:
            raise errors.RequestError(
                source_text, voice,
                f'Failed to download audio: HTTP {audio_response.status_code}'
            )

        return audio_response.content

    def _poll_prediction(self, api_key: str, prediction: dict, max_wait: int = 120) -> dict:
        """Poll a Replicate prediction until it reaches a terminal state."""
        prediction_url = prediction.get('urls', {}).get('get')
        if not prediction_url:
            prediction_id = prediction.get('id', '')
            prediction_url = f'{REPLICATE_PREDICTIONS_URL}/{prediction_id}'

        headers = {
            'Authorization': f'Bearer {api_key}',
        }

        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(1)
            try:
                resp = requests.get(prediction_url, headers=headers, timeout=30)
            except requests.exceptions.RequestException as e:
                logger.warning(f'Error polling Replicate prediction: {e}')
                continue

            if resp.status_code != 200:
                logger.warning(f'Polling returned HTTP {resp.status_code}')
                continue

            result = resp.json()
            status = result.get('status', '')
            if status in ('succeeded', 'failed', 'canceled'):
                return result

        raise errors.RequestError('', None, 'Replicate prediction timed out while polling')