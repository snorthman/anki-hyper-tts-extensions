import requests
from typing import List

from hypertts_addon import voice
from hypertts_addon import service
from hypertts_addon import errors
from hypertts_addon import constants
from hypertts_addon import languages

# For use with Local Audio Server for Yomichan Anki addon
# https://ankiweb.net/shared/info/1045800357

class YomitanLocalService(service.ServiceBase):
    def __init__(self):
        service.ServiceBase.__init__(self)
        self.preferred_keyword = ""

    @property
    def service_type(self) -> constants.ServiceType:
        return constants.ServiceType.dictionary

    @property
    def service_fee(self) -> constants.ServiceFee:
        return constants.ServiceFee.free

    def enabled_by_default(self):
        return True

    def configuration_options(self):
        return {
            'preferred_source': ['Any', 'NHK', 'Forvo', 'SMK', 'Shinmeikai']
        }

    def configure(self, config):
        self.preferred_keyword = self.get_configuration_value_optional('preferred_source', 'Any')

    def voice_list(self) -> List[voice.TtsVoice_v3]:
        return [
            voice.TtsVoice_v3(
                name='Yomitan Local Audio Server',
                gender=constants.Gender.Any,
                audio_languages=[languages.AudioLanguage.ja_JP],
                service=self.name,
                voice_key='yomitan_audio_key',
                options={},
                service_fee=self.service_fee
            ),
        ]

    def get_tts_audio(self, source_text, voice: voice.TtsVoice_v3, voice_options) -> bytes:
        search_url = "http://localhost:5050/"
        
        try:
            response = requests.get(search_url, params={'term': source_text}, timeout=5)
            if response.status_code != 200:
                raise errors.RequestError(source_text, voice, f'Server error: {response.status_code}')

            data = response.json()
            sources = data.get("audioSources", [])

            if not sources:
                raise errors.AudioNotFoundError(source_text, voice)

            selected_source = sources[0]  # Default to the first one
            
            if self.preferred_keyword != 'Any':
                for src in sources:
                    if self.preferred_keyword.lower() in src.get('name', '').lower():
                        selected_source = src
                        break 

            audio_url = selected_source.get("url")
            if not audio_url:
                raise errors.AudioNotFoundError(source_text, voice)

            audio_response = requests.get(audio_url, timeout=5)
            if audio_response.status_code == 200:
                return audio_response.content
            
            raise errors.RequestError(source_text, voice, f'Audio download error: {audio_response.status_code}')

        except Exception as e:
            raise errors.RequestError(source_text, voice, str(e))
