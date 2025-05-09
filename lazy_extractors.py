# --- START OF FILE lazy_extractors2.txt ---

import importlib
import random
import re

from ..utils import ( # Make sure these utils are still sufficient
    age_restricted,
    bug_reports_message,
    classproperty,
    variadic,
    write_string,
)

# These bloat the lazy_extractors, so allow them to passthrough silently
ALLOWED_CLASSMETHODS = {'extract_from_webpage', 'get_testcases', 'get_webpage_testcases'}
_WARNED = False


class LazyLoadMetaClass(type):
    def __getattr__(cls, name):
        global _WARNED
        if ('_real_class' not in cls.__dict__
                and name not in ALLOWED_CLASSMETHODS and not _WARNED):
            _WARNED = True
            # write_string('WARNING: Falling back to normal extractor since lazy extractor '
            #              f'{cls.__name__} does not have attribute {name}{bug_reports_message()}\n')
            # Commented out the warning to avoid console spam if it tries to access attributes
            # of extractors that are no longer "lazy" in the same way.
        return getattr(cls.real_class, name)


class LazyLoadExtractor(metaclass=LazyLoadMetaClass):
    @classproperty
    def real_class(cls):
        if '_real_class' not in cls.__dict__:
            # This will attempt to import from the original module path
            # Ensure that the _module attribute is correctly set for each defined IE below
            cls._real_class = getattr(importlib.import_module(cls._module), cls.__name__)
        return cls._real_class

    def __new__(cls, *args, **kwargs):
        # This creates an instance of the *real* class, not LazyLoadExtractor
        RealCls = cls.real_class
        instance = RealCls.__new__(RealCls) # Pass RealCls to __new__
        instance.__init__(*args, **kwargs)
        return instance

    # --- Default attributes needed by yt-dlp's core ---
    _module = None # Must be set by subclasses that are truly lazy
    _ENABLED = True
    _VALID_URL = None
    _WORKING = True
    IE_DESC = None
    IE_NAME = None # Should be set by subclasses
    _NETRC_MACHINE = None
    SEARCH_KEY = None
    age_limit = 0 # Default, YouTubeIE overrides this
    _RETURN_TYPE = None

    @classmethod
    def ie_key(cls):
        return cls.__name__[:-2] if cls.__name__.endswith('IE') else cls.__name__

    @classmethod
    def suitable(cls, url):
        if cls._VALID_URL is False: # Explicitly disabled
            return False
        if not cls._VALID_URL: # Not defined, cannot be suitable
            return False
        if '_VALID_URL_RE' not in cls.__dict__:
            cls._VALID_URL_RE = tuple(map(re.compile, variadic(cls._VALID_URL)))
        return any(regex.match(url) for regex in cls._VALID_URL_RE) # Simpler check

    @classmethod
    def _match_valid_url(cls, url): # Keep this for compatibility if called directly
        if cls._VALID_URL is False: return None
        if '_VALID_URL_RE' not in cls.__dict__:
            cls._VALID_URL_RE = tuple(map(re.compile, variadic(cls._VALID_URL)))
        return next(filter(None, (regex.match(url) for regex in cls._VALID_URL_RE)), None)


    @classmethod
    def working(cls): return cls._WORKING

    @classmethod
    def get_temp_id(cls, url):
        match = cls._match_valid_url(url)
        return match.group('id') if match and 'id' in match.groupdict() else None


    @classmethod
    def _match_id(cls, url): # This is often specific to the IE
        match = cls._match_valid_url(url)
        if match:
            try:
                return match.group('id')
            except IndexError: # No 'id' group
                return None
        return None

    @classmethod
    def description(cls, *, markdown=True, search_examples=None):
        desc = ''
        if cls._NETRC_MACHINE:
            desc += f' [*{cls._NETRC_MACHINE}*]' if markdown else f' [{cls._NETRC_MACHINE}]'
        if cls.IE_DESC is False: desc += ' [HIDDEN]'
        elif cls.IE_DESC: desc += f' {cls.IE_DESC}'
        # Simplified search key description
        if cls.SEARCH_KEY: desc += f'{";" if cls.IE_DESC else ""} "{cls.SEARCH_KEY}:" prefix'
        if not cls.working(): desc += ' (**Currently broken**)' if markdown else ' (Currently broken)'
        name_str = cls.IE_NAME or cls.ie_key()
        name = f' - **{name_str}**' if markdown else name_str
        return f'{name}:{desc}' if desc else name

    @classmethod
    def is_suitable(cls, age_limit_setting): # Renamed arg to avoid clash
        return not age_restricted(cls.age_limit, age_limit_setting)

    @classmethod
    def supports_login(cls): return bool(cls._NETRC_MACHINE)

    @classmethod
    def is_single_video(cls, url):
        if cls.suitable(url): return {'video': True, 'playlist': False}.get(cls._RETURN_TYPE)
        return None


# --- Define the IEs you want to keep ---
# For these, you are NOT using the LazyLoad mechanism in the same way.
# They are now "eagerly" defined here. The metaclass will still try to get `real_class`.
# For these specifically defined classes, `_real_class` should point to themselves.

class YoutubeBaseInfoExtractor(LazyLoadExtractor): # Make it inherit for consistency
    _module = 'yt_dlp.extractor.youtube' # Path to where the *original* full class lives
    IE_NAME = 'YoutubeBaseInfoExtract'   # Name of the class itself
    _NETRC_MACHINE = 'youtube'
    # We need to ensure real_class points to this simplified class if we are not truly lazy loading
    @classproperty
    def real_class(cls):
        # For classes defined directly in this modified file, they *are* the real class
        if '_real_class' not in cls.__dict__ or cls._real_class is None:
            cls._real_class = cls # Point to itself
        return cls._real_class

class YoutubeTabBaseInfoExtractor(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'YoutubeTabBaseInfoExtract'
    # real_class will be inherited and point to this class

class YoutubeClipIE(YoutubeTabBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:clip' # This is often used as the key
    _VALID_URL = 'https?://(?:www\\.)?youtube\\.com/clip/(?P<id>[^/?#]+)'
    _RETURN_TYPE = 'video'
    # real_class inherited

class YoutubeConsentRedirectIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:consent'
    _VALID_URL = 'https?://consent\\.youtube\\.com/m\\?'
    IE_DESC = False # Hidden
    _RETURN_TYPE = 'video' # Assuming it redirects to a video
    # real_class inherited

class YoutubeFavouritesIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:favorites'
    _VALID_URL = ':ytfav(?:ou?rite)?s?'
    IE_DESC = 'YouTube liked videos; ":ytfav" keyword (requires cookies)'
    # real_class inherited

class YoutubeFeedsInfoExtractor(YoutubeBaseInfoExtractor): # Base for feeds
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:feeds' # Not usually a directly matched IE_NAME
    # real_class inherited

class YoutubeHistoryIE(YoutubeFeedsInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:history'
    _VALID_URL = ':ythis(?:tory)?'
    IE_DESC = 'Youtube watch history; ":ythis" keyword (requires cookies)'
    # real_class inherited

class YoutubeIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube' # Key IE
    _VALID_URL = r'(?x)^(\n                         (?:https?://|//)                                    # http(s):// or protocol-independent URL\n                         (?:(?:(?:(?:\\w+\\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie|kids)?\\.com|\n                            (?:www\\.)?deturl\\.com/www\\.youtube\\.com|\n                            (?:www\\.)?pwnyoutube\\.com|\n                            (?:www\\.)?hooktube\\.com|\n                            (?:www\\.)?yourepeat\\.com|\n                            tube\\.majestyc\\.net|\n                            (?:www\\.)?redirect\\.invidious\\.io|(?:(?:www|dev)\\.)?invidio\\.us|(?:www\\.)?invidious\\.pussthecat\\.org|(?:www\\.)?invidious\\.zee\\.li|(?:www\\.)?invidious\\.ethibox\\.fr|(?:www\\.)?iv\\.ggtyler\\.dev|(?:www\\.)?inv\\.vern\\.i2p|(?:www\\.)?am74vkcrjp2d5v36lcdqgsj2m6x36tbrkhsruoegwfcizzabnfgf5zyd\\.onion|(?:www\\.)?inv\\.riverside\\.rocks|(?:www\\.)?invidious\\.silur\\.me|(?:www\\.)?inv\\.bp\\.projectsegfau\\.lt|(?:www\\.)?invidious\\.g4c3eya4clenolymqbpgwz3q3tawoxw56yhzk4vugqrl6dtu3ejvhjid\\.onion|(?:www\\.)?invidious\\.slipfox\\.xyz|(?:www\\.)?invidious\\.esmail5pdn24shtvieloeedh7ehz3nrwcdivnfhfcedl7gf4kwddhkqd\\.onion|(?:www\\.)?inv\\.vernccvbvyi5qhfzyqengccj7lkove6bjot2xhh5kajhwvidqafczrad\\.onion|(?:www\\.)?invidious\\.tiekoetter\\.com|(?:www\\.)?iv\\.odysfvr23q5wgt7i456o5t3trw2cw5dgn56vbjfbq2m7xsc5vqbqpcyd\\.onion|(?:www\\.)?invidious\\.nerdvpn\\.de|(?:www\\.)?invidious\\.weblibre\\.org|(?:www\\.)?inv\\.odyssey346\\.dev|(?:www\\.)?invidious\\.dhusch\\.de|(?:www\\.)?iv\\.melmac\\.space|(?:www\\.)?watch\\.thekitty\\.zone|(?:www\\.)?invidious\\.privacydev\\.net|(?:www\\.)?ng27owmagn5amdm7l5s3rsqxwscl5ynppnis5dqcasogkyxcfqn7psid\\.onion|(?:www\\.)?invidious\\.drivet\\.xyz|(?:www\\.)?vid\\.priv\\.au|(?:www\\.)?euxxcnhsynwmfidvhjf6uzptsmh4dipkmgdmcmxxuo7tunp3ad2jrwyd\\.onion|(?:www\\.)?inv\\.vern\\.cc|(?:www\\.)?invidious\\.esmailelbob\\.xyz|(?:www\\.)?invidious\\.sethforprivacy\\.com|(?:www\\.)?yt\\.oelrichsgarcia\\.de|(?:www\\.)?yt\\.artemislena\\.eu|(?:www\\.)?invidious\\.flokinet\\.to|(?:www\\.)?invidious\\.baczek\\.me|(?:www\\.)?y\\.com\\.sb|(?:www\\.)?invidious\\.epicsite\\.xyz|(?:www\\.)?invidious\\.lidarshield\\.cloud|(?:www\\.)?yt\\.funami\\.tech|(?:www\\.)?invidious\\.3o7z6yfxhbw7n3za4rss6l434kmv55cgw2vuziwuigpwegswvwzqipyd\\.onion|(?:www\\.)?osbivz6guyeahrwp2lnwyjk2xos342h4ocsxyqrlaopqjuhwn2djiiyd\\.onion|(?:www\\.)?u2cvlit75owumwpy4dj2hsmvkq7nvrclkpht7xgyye2pyoxhpmclkrad\\.onion|(?:(?:www|no)\\.)?invidiou\\.sh|(?:(?:www|fi)\\.)?invidious\\.snopyta\\.org|(?:www\\.)?invidious\\.kabi\\.tk|(?:www\\.)?invidious\\.mastodon\\.host|(?:www\\.)?invidious\\.zapashcanon\\.fr|(?:www\\.)?(?:invidious(?:-us)?|piped)\\.kavin\\.rocks|(?:www\\.)?invidious\\.tinfoil-hat\\.net|(?:www\\.)?invidious\\.himiko\\.cloud|(?:www\\.)?invidious\\.reallyancient\\.tech|(?:www\\.)?invidious\\.tube|(?:www\\.)?invidiou\\.site|(?:www\\.)?invidious\\.site|(?:www\\.)?invidious\\.xyz|(?:www\\.)?invidious\\.nixnet\\.xyz|(?:www\\.)?invidious\\.048596\\.xyz|(?:www\\.)?invidious\\.drycat\\.fr|(?:www\\.)?inv\\.skyn3t\\.in|(?:www\\.)?tube\\.poal\\.co|(?:www\\.)?tube\\.connect\\.cafe|(?:www\\.)?vid\\.wxzm\\.sx|(?:www\\.)?vid\\.mint\\.lgbt|(?:www\\.)?vid\\.puffyan\\.us|(?:www\\.)?yewtu\\.be|(?:www\\.)?yt\\.elukerio\\.org|(?:www\\.)?yt\\.lelux\\.fi|(?:www\\.)?invidious\\.ggc-project\\.de|(?:www\\.)?yt\\.maisputain\\.ovh|(?:www\\.)?ytprivate\\.com|(?:www\\.)?invidious\\.13ad\\.de|(?:www\\.)?invidious\\.toot\\.koeln|(?:www\\.)?invidious\\.fdn\\.fr|(?:www\\.)?watch\\.nettohikari\\.com|(?:www\\.)?invidious\\.namazso\\.eu|(?:www\\.)?invidious\\.silkky\\.cloud|(?:www\\.)?invidious\\.exonip\\.de|(?:www\\.)?invidious\\.riverside\\.rocks|(?:www\\.)?invidious\\.blamefran\\.net|(?:www\\.)?invidious\\.moomoo\\.de|(?:www\\.)?ytb\\.trom\\.tf|(?:www\\.)?yt\\.cyberhost\\.uk|(?:www\\.)?kgg2m7yk5aybusll\\.onion|(?:www\\.)?qklhadlycap4cnod\\.onion|(?:www\\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\\.onion|(?:www\\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\\.onion|(?:www\\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\\.onion|(?:www\\.)?invidious\\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\\.onion|(?:www\\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\\.b32\\.i2p|(?:www\\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\\.onion|(?:www\\.)?w6ijuptxiku4xpnnaetxvnkc5vqcdu7mgns2u77qefoixi63vbvnpnqd\\.onion|(?:www\\.)?kbjggqkzv65ivcqj6bumvp337z6264huv5kpkwuv6gu5yjiskvan7fad\\.onion|(?:www\\.)?grwp24hodrefzvjjuccrkw3mjq4tzhaaq32amf33dzpmuxe7ilepcmad\\.onion|(?:www\\.)?hpniueoejy4opn7bc4ftgazyqjoeqwlvh2uiku2xqku6zpoa4bf5ruid\\.onion|(?:www\\.)?piped\\.kavin\\.rocks|(?:www\\.)?piped\\.tokhmi\\.xyz|(?:www\\.)?piped\\.syncpundit\\.io|(?:www\\.)?piped\\.mha\\.fi|(?:www\\.)?watch\\.whatever\\.social|(?:www\\.)?piped\\.garudalinux\\.org|(?:www\\.)?piped\\.rivo\\.lol|(?:www\\.)?piped-libre\\.kavin\\.rocks|(?:www\\.)?yt\\.jae\\.fi|(?:www\\.)?piped\\.mint\\.lgbt|(?:www\\.)?il\\.ax|(?:www\\.)?piped\\.esmailelbob\\.xyz|(?:www\\.)?piped\\.projectsegfau\\.lt|(?:www\\.)?piped\\.privacydev\\.net|(?:www\\.)?piped\\.palveluntarjoaja\\.eu|(?:www\\.)?piped\\.smnz\\.de|(?:www\\.)?piped\\.adminforge\\.de|(?:www\\.)?watch\\.whatevertinfoil\\.de|(?:www\\.)?piped\\.qdi\\.fi|(?:(?:www|cf)\\.)?piped\\.video|(?:www\\.)?piped\\.aeong\\.one|(?:www\\.)?piped\\.moomoo\\.me|(?:www\\.)?piped\\.chauvet\\.pro|(?:www\\.)?watch\\.leptons\\.xyz|(?:www\\.)?pd\\.vern\\.cc|(?:www\\.)?piped\\.hostux\\.net|(?:www\\.)?piped\\.lunar\\.icu|(?:www\\.)?hyperpipe\\.surge\\.sh|(?:www\\.)?hyperpipe\\.esmailelbob\\.xyz|(?:www\\.)?listen\\.whatever\\.social|(?:www\\.)?music\\.adminforge\\.de|\n                            youtube\\.googleapis\\.com)/                        # the various hostnames, with wildcard subdomains\n                         (?:.*?\\#/)?                                          # handle anchor (#/) redirect urls\n                         (?:                                                  # the various things that can precede the ID:\n                             (?:(?:v|embed|e|shorts|live)/(?!videoseries|live_stream))  # v/ or embed/ or e/ or shorts/\n                             |(?:                                             # or the v= param in all its forms\n                                 (?:(?:watch|movie)(?:_popup)?(?:\\.php)?/?)?  # preceding watch(_popup|.php) or nothing (like /?v=xxxx)\n                                 (?:\\?|\\#!?)                                  # the params delimiter ? or # or #!\n                                 (?:.*?[&;])??                                # any other preceding param (like /?s=tuff&v=xxxx or ?s=tuff&v=V36LpHqtcDY)\n                                 v=\n                             )\n                         ))\n                         |(?:\n                            youtu\\.be|                                        # just youtu.be/xxxx\n                            vid\\.plus|                                        # or vid.plus/xxxx\n                            zwearz\\.com/watch|                                # or zwearz.com/watch/xxxx\n                            (?:www\\.)?redirect\\.invidious\\.io|(?:(?:www|dev)\\.)?invidio\\.us|(?:www\\.)?invidious\\.pussthecat\\.org|(?:www\\.)?invidious\\.zee\\.li|(?:www\\.)?invidious\\.ethibox\\.fr|(?:www\\.)?iv\\.ggtyler\\.dev|(?:www\\.)?inv\\.vern\\.i2p|(?:www\\.)?am74vkcrjp2d5v36lcdqgsj2m6x36tbrkhsruoegwfcizzabnfgf5zyd\\.onion|(?:www\\.)?inv\\.riverside\\.rocks|(?:www\\.)?invidious\\.silur\\.me|(?:www\\.)?inv\\.bp\\.projectsegfau\\.lt|(?:www\\.)?invidious\\.g4c3eya4clenolymqbpgwz3q3tawoxw56yhzk4vugqrl6dtu3ejvhjid\\.onion|(?:www\\.)?invidious\\.slipfox\\.xyz|(?:www\\.)?invidious\\.esmail5pdn24shtvieloeedh7ehz3nrwcdivnfhfcedl7gf4kwddhkqd\\.onion|(?:www\\.)?inv\\.vernccvbvyi5qhfzyqengccj7lkove6bjot2xhh5kajhwvidqafczrad\\.onion|(?:www\\.)?invidious\\.tiekoetter\\.com|(?:www\\.)?iv\\.odysfvr23q5wgt7i456o5t3trw2cw5dgn56vbjfbq2m7xsc5vqbqpcyd\\.onion|(?:www\\.)?invidious\\.nerdvpn\\.de|(?:www\\.)?invidious\\.weblibre\\.org|(?:www\\.)?inv\\.odyssey346\\.dev|(?:www\\.)?invidious\\.dhusch\\.de|(?:www\\.)?iv\\.melmac\\.space|(?:www\\.)?watch\\.thekitty\\.zone|(?:www\\.)?invidious\\.privacydev\\.net|(?:www\\.)?ng27owmagn5amdm7l5s3rsqxwscl5ynppnis5dqcasogkyxcfqn7psid\\.onion|(?:www\\.)?invidious\\.drivet\\.xyz|(?:www\\.)?vid\\.priv\\.au|(?:www\\.)?euxxcnhsynwmfidvhjf6uzptsmh4dipkmgdmcmxxuo7tunp3ad2jrwyd\\.onion|(?:www\\.)?inv\\.vern\\.cc|(?:www\\.)?invidious\\.esmailelbob\\.xyz|(?:www\\.)?invidious\\.sethforprivacy\\.com|(?:www\\.)?yt\\.oelrichsgarcia\\.de|(?:www\\.)?yt\\.artemislena\\.eu|(?:www\\.)?invidious\\.flokinet\\.to|(?:www\\.)?invidious\\.baczek\\.me|(?:www\\.)?y\\.com\\.sb|(?:www\\.)?invidious\\.epicsite\\.xyz|(?:www\\.)?invidious\\.lidarshield\\.cloud|(?:www\\.)?yt\\.funami\\.tech|(?:www\\.)?invidious\\.3o7z6yfxhbw7n3za4rss6l434kmv55cgw2vuziwuigpwegswvwzqipyd\\.onion|(?:www\\.)?osbivz6guyeahrwp2lnwyjk2xos342h4ocsxyqrlaopqjuhwn2djiiyd\\.onion|(?:www\\.)?u2cvlit75owumwpy4dj2hsmvkq7nvrclkpht7xgyye2pyoxhpmclkrad\\.onion|(?:(?:www|no)\\.)?invidiou\\.sh|(?:(?:www|fi)\\.)?invidious\\.snopyta\\.org|(?:www\\.)?invidious\\.kabi\\.tk|(?:www\\.)?invidious\\.mastodon\\.host|(?:www\\.)?invidious\\.zapashcanon\\.fr|(?:www\\.)?(?:invidious(?:-us)?|piped)\\.kavin\\.rocks|(?:www\\.)?invidious\\.tinfoil-hat\\.net|(?:www\\.)?invidious\\.himiko\\.cloud|(?:www\\.)?invidious\\.reallyancient\\.tech|(?:www\\.)?invidious\\.tube|(?:www\\.)?invidiou\\.site|(?:www\\.)?invidious\\.site|(?:www\\.)?invidious\\.xyz|(?:www\\.)?invidious\\.nixnet\\.xyz|(?:www\\.)?invidious\\.048596\\.xyz|(?:www\\.)?invidious\\.drycat\\.fr|(?:www\\.)?inv\\.skyn3t\\.in|(?:www\\.)?tube\\.poal\\.co|(?:www\\.)?tube\\.connect\\.cafe|(?:www\\.)?vid\\.wxzm\\.sx|(?:www\\.)?vid\\.mint\\.lgbt|(?:www\\.)?vid\\.puffyan\\.us|(?:www\\.)?yewtu\\.be|(?:www\\.)?yt\\.elukerio\\.org|(?:www\\.)?yt\\.lelux\\.fi|(?:www\\.)?invidious\\.ggc-project\\.de|(?:www\\.)?yt\\.maisputain\\.ovh|(?:www\\.)?ytprivate\\.com|(?:www\\.)?invidious\\.13ad\\.de|(?:www\\.)?invidious\\.toot\\.koeln|(?:www\\.)?invidious\\.fdn\\.fr|(?:www\\.)?watch\\.nettohikari\\.com|(?:www\\.)?invidious\\.namazso\\.eu|(?:www\\.)?invidious\\.silkky\\.cloud|(?:www\\.)?invidious\\.exonip\\.de|(?:www\\.)?invidious\\.riverside\\.rocks|(?:www\\.)?invidious\\.blamefran\\.net|(?:www\\.)?invidious\\.moomoo\\.de|(?:www\\.)?ytb\\.trom\\.tf|(?:www\\.)?yt\\.cyberhost\\.uk|(?:www\\.)?kgg2m7yk5aybusll\\.onion|(?:www\\.)?qklhadlycap4cnod\\.onion|(?:www\\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\\.onion|(?:www\\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\\.onion|(?:www\\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\\.onion|(?:www\\.)?invidious\\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\\.onion|(?:www\\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\\.b32\\.i2p|(?:www\\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\\.onion|(?:www\\.)?w6ijuptxiku4xpnnaetxvnkc5vqcdu7mgns2u77qefoixi63vbvnpnqd\\.onion|(?:www\\.)?kbjggqkzv65ivcqj6bumvp337z6264huv5kpkwuv6gu5yjiskvan7fad\\.onion|(?:www\\.)?grwp24hodrefzvjjuccrkw3mjq4tzhaaq32amf33dzpmuxe7ilepcmad\\.onion|(?:www\\.)?hpniueoejy4opn7bc4ftgazyqjoeqwlvh2uiku2xqku6zpoa4bf5ruid\\.onion|(?:www\\.)?piped\\.kavin\\.rocks|(?:www\\.)?piped\\.tokhmi\\.xyz|(?:www\\.)?piped\\.syncpundit\\.io|(?:www\\.)?piped\\.mha\\.fi|(?:www\\.)?watch\\.whatever\\.social|(?:www\\.)?piped\\.garudalinux\\.org|(?:www\\.)?piped\\.rivo\\.lol|(?:www\\.)?piped-libre\\.kavin\\.rocks|(?:www\\.)?yt\\.jae\\.fi|(?:www\\.)?piped\\.mint\\.lgbt|(?:www\\.)?il\\.ax|(?:www\\.)?piped\\.esmailelbob\\.xyz|(?:www\\.)?piped\\.projectsegfau\\.lt|(?:www\\.)?piped\\.privacydev\\.net|(?:www\\.)?piped\\.palveluntarjoaja\\.eu|(?:www\\.)?piped\\.smnz\\.de|(?:www\\.)?piped\\.adminforge\\.de|(?:www\\.)?watch\\.whatevertinfoil\\.de|(?:www\\.)?piped\\.qdi\\.fi|(?:(?:www|cf)\\.)?piped\\.video|(?:www\\.)?piped\\.aeong\\.one|(?:www\\.)?piped\\.moomoo\\.me|(?:www\\.)?piped\\.chauvet\\.pro|(?:www\\.)?watch\\.leptons\\.xyz|(?:www\\.)?pd\\.vern\\.cc|(?:www\\.)?piped\\.hostux\\.net|(?:www\\.)?piped\\.lunar\\.icu|(?:www\\.)?hyperpipe\\.surge\\.sh|(?:www\\.)?hyperpipe\\.esmailelbob\\.xyz|(?:www\\.)?listen\\.whatever\\.social|(?:www\\.)?music\\.adminforge\\.de\n                         )/\n                         |(?:www\\.)?cleanvideosearch\\.com/media/action/yt/watch\\?videoId=\n                         )\n                     )?                                                       # all until now is optional -> you can pass the naked ID\n                     (?P<id>[0-9A-Za-z_-]{11})                              # here is it! the YouTube video ID\n                     (?(1).+)?                                                # if we found the ID, everything can follow\n                     (?:\\#|$)' # Shortened for brevity, use the original long regex
    IE_DESC = 'YouTube'
    age_limit = 18 # YouTube videos can be age restricted
    _RETURN_TYPE = 'video'
    # real_class inherited

    @classmethod
    def suitable(cls, url): # Overridden from YoutubeBaseInfoExtractor
        # This is a simplified version. The original is more complex.
        # You might need to port more logic from the original YoutubeIE.suitable
        # if you encounter issues with playlist URLs being misidentified.
        if 'list=' in url and 'watch?v=' in url : # Basic check for video in playlist
             return True # It's a video, even if part of a playlist context
        if 'list=' in url :
             return False # It's primarily a playlist URL
        return super().suitable(url)


class YoutubeLivestreamEmbedIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'YoutubeLivestreamEmbed'
    _VALID_URL = r'https?://(?:\w+\.)?youtube\.com/embed/live_stream/?\?(?:[^#]+&)?channel=(?P<id>[^&#]+)'
    IE_DESC = 'YouTube livestream embeds'
    # real_class inherited

class YoutubeMusicSearchURLIE(YoutubeTabBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:music:search_url'
    _VALID_URL = r'https?://music\.youtube\.com/search\?([^#]+&)?(?:search_query|q)=(?:[^&]+)(?:[&#]|$)'
    IE_DESC = 'YouTube music search URLs with selectable sections, e.g. #songs'
    _RETURN_TYPE = 'playlist'
    # real_class inherited

class YoutubeNotificationsIE(YoutubeTabBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:notif'
    _VALID_URL = r':ytnotif(?:ication)?s?'
    IE_DESC = 'YouTube notifications; ":ytnotif" keyword (requires cookies)'
    # real_class inherited

class YoutubePlaylistIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:playlist'
    _VALID_URL = r'(?x)(?:\n                        (?:https?://)?\n                        (?:\\w+\\.)?\n                        (?:\n                            (?:\n                                youtube(?:kids)?\\.com|\n                                (?:www\\.)?redirect\\.invidious\\.io|(?:(?:www|dev)\\.)?invidio\\.us|(?:www\\.)?invidious\\.pussthecat\\.org|(?:www\\.)?invidious\\.zee\\.li|(?:www\\.)?invidious\\.ethibox\\.fr|(?:www\\.)?iv\\.ggtyler\\.dev|(?:www\\.)?inv\\.vern\\.i2p|(?:www\\.)?am74vkcrjp2d5v36lcdqgsj2m6x36tbrkhsruoegwfcizzabnfgf5zyd\\.onion|(?:www\\.)?inv\\.riverside\\.rocks|(?:www\\.)?invidious\\.silur\\.me|(?:www\\.)?inv\\.bp\\.projectsegfau\\.lt|(?:www\\.)?invidious\\.g4c3eya4clenolymqbpgwz3q3tawoxw56yhzk4vugqrl6dtu3ejvhjid\\.onion|(?:www\\.)?invidious\\.slipfox\\.xyz|(?:www\\.)?invidious\\.esmail5pdn24shtvieloeedh7ehz3nrwcdivnfhfcedl7gf4kwddhkqd\\.onion|(?:www\\.)?inv\\.vernccvbvyi5qhfzyqengccj7lkove6bjot2xhh5kajhwvidqafczrad\\.onion|(?:www\\.)?invidious\\.tiekoetter\\.com|(?:www\\.)?iv\\.odysfvr23q5wgt7i456o5t3trw2cw5dgn56vbjfbq2m7xsc5vqbqpcyd\\.onion|(?:www\\.)?invidious\\.nerdvpn\\.de|(?:www\\.)?invidious\\.weblibre\\.org|(?:www\\.)?inv\\.odyssey346\\.dev|(?:www\\.)?invidious\\.dhusch\\.de|(?:www\\.)?iv\\.melmac\\.space|(?:www\\.)?watch\\.thekitty\\.zone|(?:www\\.)?invidious\\.privacydev\\.net|(?:www\\.)?ng27owmagn5amdm7l5s3rsqxwscl5ynppnis5dqcasogkyxcfqn7psid\\.onion|(?:www\\.)?invidious\\.drivet\\.xyz|(?:www\\.)?vid\\.priv\\.au|(?:www\\.)?euxxcnhsynwmfidvhjf6uzptsmh4dipkmgdmcmxxuo7tunp3ad2jrwyd\\.onion|(?:www\\.)?inv\\.vern\\.cc|(?:www\\.)?invidious\\.esmailelbob\\.xyz|(?:www\\.)?invidious\\.sethforprivacy\\.com|(?:www\\.)?yt\\.oelrichsgarcia\\.de|(?:www\\.)?yt\\.artemislena\\.eu|(?:www\\.)?invidious\\.flokinet\\.to|(?:www\\.)?invidious\\.baczek\\.me|(?:www\\.)?y\\.com\\.sb|(?:www\\.)?invidious\\.epicsite\\.xyz|(?:www\\.)?invidious\\.lidarshield\\.cloud|(?:www\\.)?yt\\.funami\\.tech|(?:www\\.)?invidious\\.3o7z6yfxhbw7n3za4rss6l434kmv55cgw2vuziwuigpwegswvwzqipyd\\.onion|(?:www\\.)?osbivz6guyeahrwp2lnwyjk2xos342h4ocsxyqrlaopqjuhwn2djiiyd\\.onion|(?:www\\.)?u2cvlit75owumwpy4dj2hsmvkq7nvrclkpht7xgyye2pyoxhpmclkrad\\.onion|(?:(?:www|no)\\.)?invidiou\\.sh|(?:(?:www|fi)\\.)?invidious\\.snopyta\\.org|(?:www\\.)?invidious\\.kabi\\.tk|(?:www\\.)?invidious\\.mastodon\\.host|(?:www\\.)?invidious\\.zapashcanon\\.fr|(?:www\\.)?(?:invidious(?:-us)?|piped)\\.kavin\\.rocks|(?:www\\.)?invidious\\.tinfoil-hat\\.net|(?:www\\.)?invidious\\.himiko\\.cloud|(?:www\\.)?invidious\\.reallyancient\\.tech|(?:www\\.)?invidious\\.tube|(?:www\\.)?invidiou\\.site|(?:www\\.)?invidious\\.site|(?:www\\.)?invidious\\.xyz|(?:www\\.)?invidious\\.nixnet\\.xyz|(?:www\\.)?invidious\\.048596\\.xyz|(?:www\\.)?invidious\\.drycat\\.fr|(?:www\\.)?inv\\.skyn3t\\.in|(?:www\\.)?tube\\.poal\\.co|(?:www\\.)?tube\\.connect\\.cafe|(?:www\\.)?vid\\.wxzm\\.sx|(?:www\\.)?vid\\.mint\\.lgbt|(?:www\\.)?vid\\.puffyan\\.us|(?:www\\.)?yewtu\\.be|(?:www\\.)?yt\\.elukerio\\.org|(?:www\\.)?yt\\.lelux\\.fi|(?:www\\.)?invidious\\.ggc-project\\.de|(?:www\\.)?yt\\.maisputain\\.ovh|(?:www\\.)?ytprivate\\.com|(?:www\\.)?invidious\\.13ad\\.de|(?:www\\.)?invidious\\.toot\\.koeln|(?:www\\.)?invidious\\.fdn\\.fr|(?:www\\.)?watch\\.nettohikari\\.com|(?:www\\.)?invidious\\.namazso\\.eu|(?:www\\.)?invidious\\.silkky\\.cloud|(?:www\\.)?invidious\\.exonip\\.de|(?:www\\.)?invidious\\.riverside\\.rocks|(?:www\\.)?invidious\\.blamefran\\.net|(?:www\\.)?invidious\\.moomoo\\.de|(?:www\\.)?ytb\\.trom\\.tf|(?:www\\.)?yt\\.cyberhost\\.uk|(?:www\\.)?kgg2m7yk5aybusll\\.onion|(?:www\\.)?qklhadlycap4cnod\\.onion|(?:www\\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\\.onion|(?:www\\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\\.onion|(?:www\\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\\.onion|(?:www\\.)?invidious\\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\\.onion|(?:www\\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\\.b32\\.i2p|(?:www\\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\\.onion|(?:www\\.)?w6ijuptxiku4xpnnaetxvnkc5vqcdu7mgns2u77qefoixi63vbvnpnqd\\.onion|(?:www\\.)?kbjggqkzv65ivcqj6bumvp337z6264huv5kpkwuv6gu5yjiskvan7fad\\.onion|(?:www\\.)?grwp24hodrefzvjjuccrkw3mjq4tzhaaq32amf33dzpmuxe7ilepcmad\\.onion|(?:www\\.)?hpniueoejy4opn7bc4ftgazyqjoeqwlvh2uiku2xqku6zpoa4bf5ruid\\.onion|(?:www\\.)?piped\\.kavin\\.rocks|(?:www\\.)?piped\\.tokhmi\\.xyz|(?:www\\.)?piped\\.syncpundit\\.io|(?:www\\.)?piped\\.mha\\.fi|(?:www\\.)?watch\\.whatever\\.social|(?:www\\.)?piped\\.garudalinux\\.org|(?:www\\.)?piped\\.rivo\\.lol|(?:www\\.)?piped-libre\\.kavin\\.rocks|(?:www\\.)?yt\\.jae\\.fi|(?:www\\.)?piped\\.mint\\.lgbt|(?:www\\.)?il\\.ax|(?:www\\.)?piped\\.esmailelbob\\.xyz|(?:www\\.)?piped\\.projectsegfau\\.lt|(?:www\\.)?piped\\.privacydev\\.net|(?:www\\.)?piped\\.palveluntarjoaja\\.eu|(?:www\\.)?piped\\.smnz\\.de|(?:www\\.)?piped\\.adminforge\\.de|(?:www\\.)?watch\\.whatevertinfoil\\.de|(?:www\\.)?piped\\.qdi\\.fi|(?:(?:www|cf)\\.)?piped\\.video|(?:www\\.)?piped\\.aeong\\.one|(?:www\\.)?piped\\.moomoo\\.me|(?:www\\.)?piped\\.chauvet\\.pro|(?:www\\.)?watch\\.leptons\\.xyz|(?:www\\.)?pd\\.vern\\.cc|(?:www\\.)?piped\\.hostux\\.net|(?:www\\.)?piped\\.lunar\\.icu|(?:www\\.)?hyperpipe\\.surge\\.sh|(?:www\\.)?hyperpipe\\.esmailelbob\\.xyz|(?:www\\.)?listen\\.whatever\\.social|(?:www\\.)?music\\.adminforge\\.de\n                            )\n                            /.*?\\?.*?\\blist=\n                        )?\n                        (?P<id>(?:(?:PL|LL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)[0-9A-Za-z-_]{10,}|RDMM|WL|LL|LM))\n                     )' # Shortened for brevity
    IE_DESC = 'YouTube playlists'
    _RETURN_TYPE = 'playlist'
    # real_class inherited

    @classmethod
    def suitable(cls, url): # Overridden
        # Simplified version
        if 'watch?v=' in url and 'list=' in url:
            return False # Let YoutubeIE handle video in playlist context
        return super().suitable(url)


class YoutubeRecommendedIE(YoutubeFeedsInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:recommended'
    _VALID_URL = r'https?://(?:www\\.)?youtube\\.com/?(?:[?#]|$)|:ytrec(?:ommended)?'
    IE_DESC = 'YouTube recommended videos; ":ytrec" keyword'
    # real_class inherited

class LazyLoadSearchExtractor(LazyLoadExtractor): # Ensure this base class exists
    _module = 'yt_dlp.extractor.youtube' # Or wherever its original definition might be if it had one
    IE_NAME = 'LazyLoadSearchExtractor'
    # real_class inherited or points to self if it's meant to be concrete in this file

class YoutubeSearchDateIE(YoutubeTabBaseInfoExtractor, LazyLoadSearchExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:search:date'
    _VALID_URL = r'ytsearchdate(?P<prefix>|[1-9][0-9]*|all):(?P<query>[\s\S]+)'
    IE_DESC = 'YouTube search, newest videos first'
    SEARCH_KEY = 'ytsearchdate'
    _RETURN_TYPE = 'playlist'
    # real_class inherited

class YoutubeSearchIE(YoutubeTabBaseInfoExtractor, LazyLoadSearchExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:search'
    _VALID_URL = r'ytsearch(?P<prefix>|[1-9][0-9]*|all):(?P<query>[\s\S]+)'
    IE_DESC = 'YouTube search'
    SEARCH_KEY = 'ytsearch'
    _RETURN_TYPE = 'playlist'
    # real_class inherited

class YoutubeSearchURLIE(YoutubeTabBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:search_url'
    _VALID_URL = r'https?://(?:www\\.)?youtube\\.com/(?:results|search)\?([^#]+&)?(?:search_query|q)=(?:[^&]+)(?:[&#]|$)'
    IE_DESC = 'YouTube search URLs with sorting and filter support'
    _RETURN_TYPE = 'playlist'
    # real_class inherited

class YoutubeShortsAudioPivotIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:shorts:pivot:audio'
    _VALID_URL = r'https?://(?:www\\.)?youtube\\.com/source/(?P<id>[\w-]{11})/shorts'
    IE_DESC = 'YouTube Shorts audio pivot (Shorts using audio of a given video)'
    # real_class inherited

class YoutubeSubscriptionsIE(YoutubeFeedsInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:subscriptions'
    _VALID_URL = r':ytsub(?:scription)?s?'
    IE_DESC = 'YouTube subscriptions feed; ":ytsubs" keyword (requires cookies)'
    # real_class inherited

class YoutubeTabIE(YoutubeTabBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:tab'
    _VALID_URL = r'(?x:        https?://\n            (?!consent\\.)(?:\\w+\\.)?\n            (?:\n                youtube(?:kids)?\\.com|\n                (?:www\\.)?redirect\\.invidious\\.io|(?:(?:www|dev)\\.)?invidio\\.us|(?:www\\.)?invidious\\.pussthecat\\.org|(?:www\\.)?invidious\\.zee\\.li|(?:www\\.)?invidious\\.ethibox\\.fr|(?:www\\.)?iv\\.ggtyler\\.dev|(?:www\\.)?inv\\.vern\\.i2p|(?:www\\.)?am74vkcrjp2d5v36lcdqgsj2m6x36tbrkhsruoegwfcizzabnfgf5zyd\\.onion|(?:www\\.)?inv\\.riverside\\.rocks|(?:www\\.)?invidious\\.silur\\.me|(?:www\\.)?inv\\.bp\\.projectsegfau\\.lt|(?:www\\.)?invidious\\.g4c3eya4clenolymqbpgwz3q3tawoxw56yhzk4vugqrl6dtu3ejvhjid\\.onion|(?:www\\.)?invidious\\.slipfox\\.xyz|(?:www\\.)?invidious\\.esmail5pdn24shtvieloeedh7ehz3nrwcdivnfhfcedl7gf4kwddhkqd\\.onion|(?:www\\.)?inv\\.vernccvbvyi5qhfzyqengccj7lkove6bjot2xhh5kajhwvidqafczrad\\.onion|(?:www\\.)?invidious\\.tiekoetter\\.com|(?:www\\.)?iv\\.odysfvr23q5wgt7i456o5t3trw2cw5dgn56vbjfbq2m7xsc5vqbqpcyd\\.onion|(?:www\\.)?invidious\\.nerdvpn\\.de|(?:www\\.)?invidious\\.weblibre\\.org|(?:www\\.)?inv\\.odyssey346\\.dev|(?:www\\.)?invidious\\.dhusch\\.de|(?:www\\.)?iv\\.melmac\\.space|(?:www\\.)?watch\\.thekitty\\.zone|(?:www\\.)?invidious\\.privacydev\\.net|(?:www\\.)?ng27owmagn5amdm7l5s3rsqxwscl5ynppnis5dqcasogkyxcfqn7psid\\.onion|(?:www\\.)?invidious\\.drivet\\.xyz|(?:www\\.)?vid\\.priv\\.au|(?:www\\.)?euxxcnhsynwmfidvhjf6uzptsmh4dipkmgdmcmxxuo7tunp3ad2jrwyd\\.onion|(?:www\\.)?inv\\.vern\\.cc|(?:www\\.)?invidious\\.esmailelbob\\.xyz|(?:www\\.)?invidious\\.sethforprivacy\\.com|(?:www\\.)?yt\\.oelrichsgarcia\\.de|(?:www\\.)?yt\\.artemislena\\.eu|(?:www\\.)?invidious\\.flokinet\\.to|(?:www\\.)?invidious\\.baczek\\.me|(?:www\\.)?y\\.com\\.sb|(?:www\\.)?invidious\\.epicsite\\.xyz|(?:www\\.)?invidious\\.lidarshield\\.cloud|(?:www\\.)?yt\\.funami\\.tech|(?:www\\.)?invidious\\.3o7z6yfxhbw7n3za4rss6l434kmv55cgw2vuziwuigpwegswvwzqipyd\\.onion|(?:www\\.)?osbivz6guyeahrwp2lnwyjk2xos342h4ocsxyqrlaopqjuhwn2djiiyd\\.onion|(?:www\\.)?u2cvlit75owumwpy4dj2hsmvkq7nvrclkpht7xgyye2pyoxhpmclkrad\\.onion|(?:(?:www|no)\\.)?invidiou\\.sh|(?:(?:www|fi)\\.)?invidious\\.snopyta\\.org|(?:www\\.)?invidious\\.kabi\\.tk|(?:www\\.)?invidious\\.mastodon\\.host|(?:www\\.)?invidious\\.zapashcanon\\.fr|(?:www\\.)?(?:invidious(?:-us)?|piped)\\.kavin\\.rocks|(?:www\\.)?invidious\\.tinfoil-hat\\.net|(?:www\\.)?invidious\\.himiko\\.cloud|(?:www\\.)?invidious\\.reallyancient\\.tech|(?:www\\.)?invidious\\.tube|(?:www\\.)?invidiou\\.site|(?:www\\.)?invidious\\.site|(?:www\\.)?invidious\\.xyz|(?:www\\.)?invidious\\.nixnet\\.xyz|(?:www\\.)?invidious\\.048596\\.xyz|(?:www\\.)?invidious\\.drycat\\.fr|(?:www\\.)?inv\\.skyn3t\\.in|(?:www\\.)?tube\\.poal\\.co|(?:www\\.)?tube\\.connect\\.cafe|(?:www\\.)?vid\\.wxzm\\.sx|(?:www\\.)?vid\\.mint\\.lgbt|(?:www\\.)?vid\\.puffyan\\.us|(?:www\\.)?yewtu\\.be|(?:www\\.)?yt\\.elukerio\\.org|(?:www\\.)?yt\\.lelux\\.fi|(?:www\\.)?invidious\\.ggc-project\\.de|(?:www\\.)?yt\\.maisputain\\.ovh|(?:www\\.)?ytprivate\\.com|(?:www\\.)?invidious\\.13ad\\.de|(?:www\\.)?invidious\\.toot\\.koeln|(?:www\\.)?invidious\\.fdn\\.fr|(?:www\\.)?watch\\.nettohikari\\.com|(?:www\\.)?invidious\\.namazso\\.eu|(?:www\\.)?invidious\\.silkky\\.cloud|(?:www\\.)?invidious\\.exonip\\.de|(?:www\\.)?invidious\\.riverside\\.rocks|(?:www\\.)?invidious\\.blamefran\\.net|(?:www\\.)?invidious\\.moomoo\\.de|(?:www\\.)?ytb\\.trom\\.tf|(?:www\\.)?yt\\.cyberhost\\.uk|(?:www\\.)?kgg2m7yk5aybusll\\.onion|(?:www\\.)?qklhadlycap4cnod\\.onion|(?:www\\.)?axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4bzzsg2ii4fv2iid\\.onion|(?:www\\.)?c7hqkpkpemu6e7emz5b4vyz7idjgdvgaaa3dyimmeojqbgpea3xqjoid\\.onion|(?:www\\.)?fz253lmuao3strwbfbmx46yu7acac2jz27iwtorgmbqlkurlclmancad\\.onion|(?:www\\.)?invidious\\.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd\\.onion|(?:www\\.)?owxfohz4kjyv25fvlqilyxast7inivgiktls3th44jhk3ej3i7ya\\.b32\\.i2p|(?:www\\.)?4l2dgddgsrkf2ous66i6seeyi6etzfgrue332grh2n7madpwopotugyd\\.onion|(?:www\\.)?w6ijuptxiku4xpnnaetxvnkc5vqcdu7mgns2u77qefoixi63vbvnpnqd\\.onion|(?:www\\.)?kbjggqkzv65ivcqj6bumvp337z6264huv5kpkwuv6gu5yjiskvan7fad\\.onion|(?:www\\.)?grwp24hodrefzvjjuccrkw3mjq4tzhaaq32amf33dzpmuxe7ilepcmad\\.onion|(?:www\\.)?hpniueoejy4opn7bc4ftgazyqjoeqwlvh2uiku2xqku6zpoa4bf5ruid\\.onion|(?:www\\.)?piped\\.kavin\\.rocks|(?:www\\.)?piped\\.tokhmi\\.xyz|(?:www\\.)?piped\\.syncpundit\\.io|(?:www\\.)?piped\\.mha\\.fi|(?:www\\.)?watch\\.whatever\\.social|(?:www\\.)?piped\\.garudalinux\\.org|(?:www\\.)?piped\\.rivo\\.lol|(?:www\\.)?piped-libre\\.kavin\\.rocks|(?:www\\.)?yt\\.jae\\.fi|(?:www\\.)?piped\\.mint\\.lgbt|(?:www\\.)?il\\.ax|(?:www\\.)?piped\\.esmailelbob\\.xyz|(?:www\\.)?piped\\.projectsegfau\\.lt|(?:www\\.)?piped\\.privacydev\\.net|(?:www\\.)?piped\\.palveluntarjoaja\\.eu|(?:www\\.)?piped\\.smnz\\.de|(?:www\\.)?piped\\.adminforge\\.de|(?:www\\.)?watch\\.whatevertinfoil\\.de|(?:www\\.)?piped\\.qdi\\.fi|(?:(?:www|cf)\\.)?piped\\.video|(?:www\\.)?piped\\.aeong\\.one|(?:www\\.)?piped\\.moomoo\\.me|(?:www\\.)?piped\\.chauvet\\.pro|(?:www\\.)?watch\\.leptons\\.xyz|(?:www\\.)?pd\\.vern\\.cc|(?:www\\.)?piped\\.hostux\\.net|(?:www\\.)?piped\\.lunar\\.icu|(?:www\\.)?hyperpipe\\.surge\\.sh|(?:www\\.)?hyperpipe\\.esmailelbob\\.xyz|(?:www\\.)?listen\\.whatever\\.social|(?:www\\.)?music\\.adminforge\\.de\n            )/\n            (?:\n                (?P<channel_type>channel|c|user|browse)/|\n                (?P<not_channel>\n                    feed/|hashtag/|\n                    (?:playlist|watch)\\?.*?\\blist=\n                )|\n                (?!(?:channel|c|user|playlist|watch|w|v|embed|e|live|watch_popup|clip|shorts|movies|results|search|shared|hashtag|trending|explore|feed|feeds|browse|oembed|get_video_info|iframe_api|s/player|source|storefront|oops|index|account|t/terms|about|upload|signin|logout)\\b)  # Direct URLs\n            )\n            (?P<id>[^/?\\#&]+)\n    )' # Shortened
    IE_DESC = 'YouTube Tabs'
    _RETURN_TYPE = 'any' # Can be channel, playlist, etc.
    # real_class inherited

    @classmethod
    def suitable(cls, url): # Overridden
        return False if YoutubeIE.suitable(url) else super().suitable(url)


class YoutubeTruncatedIDIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:truncated_id'
    _VALID_URL = r'https?://(?:www\\.)?youtube\\.com/watch\\?v=(?P<id>[0-9A-Za-z_-]{1,10})$'
    IE_DESC = False # Hidden
    # real_class inherited

class YoutubeTruncatedURLIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:truncated_url'
    _VALID_URL = r'(?x)\n        (?:https?://)?\n        (?:\\w+\\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie)?\\.com/\n        (?:watch\\?(?:\n            feature=[a-z_]+|\n            annotation_id=annotation_[^&]+|\n            x-yt-cl=[0-9]+|\n            hl=[^&]*|\n            t=[0-9]+\n        )?\n        |\n            attribution_link\\?a=[^&]+\n        )\n        $\n    ' # Shortened
    IE_DESC = False # Hidden
    # real_class inherited

class YoutubeWatchLaterIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:watchlater'
    _VALID_URL = r':ytwatchlater'
    IE_DESC = 'Youtube watch later list; ":ytwatchlater" keyword (requires cookies)'
    # real_class inherited

class YoutubeWebArchiveIE(LazyLoadExtractor): # Inherit from your base
    _module = 'yt_dlp.extractor.archiveorg' # Path to original full class
    IE_NAME = 'web.archive:youtube'
    _VALID_URL = r'(?x)(?:(?P<prefix>ytarchive:)|\n            (?:https?://)?web\\.archive\\.org/\n            (?:web/)?(?:(?P<date>[0-9]{14})?[0-9A-Za-z_*]*/)?\n            (?:https?(?::|%3[Aa])//)?(?:\n                (?:\\w+\\.)?youtube\\.com(?::(?:80|443))?/watch(?:\\.php)?(?:\\?|%3[fF])(?:[^\\#]+(?:&|%26))?v(?:=|%3[dD])\n                |(?:wayback-fakeurl\\.archive\\.org/yt/)\n            )\n        )(?P<id>[0-9A-Za-z_-]{11})\n        (?(prefix)\n            (?::(?P<date2>[0-9]{14}))?$|\n            (?:%26|[#&]|$)\n        )' # Shortened
    IE_DESC = 'web.archive.org saved youtube videos, "ytarchive:" prefix'
    _RETURN_TYPE = 'video'
    @classproperty # Override for this one
    def real_class(cls):
        if '_real_class' not in cls.__dict__ or cls._real_class is None:
            cls._real_class = cls 
        return cls._real_class


class YoutubeYtBeIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'YoutubeYtBe' # Original used IE_NAME = 'youtube'
    _VALID_URL = r'https?://youtu\\.be/(?P<id>[0-9A-Za-z_-]{11})/*?.*?\\blist=(?P<playlist_id>(?:(?:PL|LL|EC|UU|FL|RD|UL|TL|PU|OLAK5uy_)[0-9A-Za-z-_]{10,}|RDMM|WL|LL|LM))'
    IE_DESC = 'youtu.be' # Original used 'Youtube'
    _RETURN_TYPE = 'video' # Or 'playlist' depending on which part is matched
    # real_class inherited

class YoutubeYtUserIE(YoutubeBaseInfoExtractor):
    _module = 'yt_dlp.extractor.youtube'
    IE_NAME = 'youtube:user'
    _VALID_URL = r'ytuser:(?P<id>.+)'
    IE_DESC = 'YouTube user videos; "ytuser:" prefix'
    # real_class inherited


# --- Generic Extractor ---
class GenericIE(LazyLoadExtractor): # Inherit from your base
    _module = 'yt_dlp.extractor.generic' # Path to original full class
    IE_NAME = 'generic'
    _VALID_URL = r'.*' # Matches any URL as a fallback
    IE_DESC = 'Generic downloader that works on some sites'
    _NETRC_MACHINE = False # Explicitly
    age_limit = 18 # Default, can be overridden
    _RETURN_TYPE = 'any' # Can be anything
    @classproperty # Override for this one
    def real_class(cls):
        if '_real_class' not in cls.__dict__ or cls._real_class is None:
            cls._real_class = cls # Itself
        return cls._real_class

# --- THE CORRECTED _CLASS_LOOKUP ---
# It should only contain the IE_NAME (or ie_key) of the classes DEFINED in *this* file.
# The key in _CLASS_LOOKUP is usually the class name itself (e.g., 'YoutubeIE')
# or sometimes a more specific key if the class's ie_key() method returns something different.
# For simplicity and directness here, let's map the IE_NAME.
# yt-dlp's core uses ie.ie_key() to get the key for the lookup.

_CLASS_LOOKUP = {
    # Kinja (if you decide to keep it, otherwise remove)
    # 'KinjaEmbedIE': KinjaEmbedIE, # Original key might be 'kinja:embed'

    # PeerTube (if you keep it, otherwise remove)
    # 'PeerTubeIE': PeerTubeIE, # Original key might be 'PeerTube'
    # 'PeerTubePlaylistIE': PeerTubePlaylistIE, # Original key might be 'PeerTube:playlist'

    # YouTube Extractors - Their ie_key() usually returns the IE_NAME without "IE"
    # or a specific string like "youtube".
    # yt-dlp often uses `ie_key()` for lookup. Let's try to match that.
    YoutubeClipIE.ie_key(): YoutubeClipIE,
    YoutubeConsentRedirectIE.ie_key(): YoutubeConsentRedirectIE,
    YoutubeFavouritesIE.ie_key(): YoutubeFavouritesIE,
    YoutubeHistoryIE.ie_key(): YoutubeHistoryIE,
    YoutubeIE.ie_key(): YoutubeIE, # This is crucial, its ie_key() is 'Youtube'
    YoutubeLivestreamEmbedIE.ie_key(): YoutubeLivestreamEmbedIE,
    YoutubeMusicSearchURLIE.ie_key(): YoutubeMusicSearchURLIE,
    YoutubeNotificationsIE.ie_key(): YoutubeNotificationsIE,
    YoutubePlaylistIE.ie_key(): YoutubePlaylistIE, # Its ie_key() is 'Youtube:playlist'
    YoutubeRecommendedIE.ie_key(): YoutubeRecommendedIE,
    YoutubeSearchDateIE.ie_key(): YoutubeSearchDateIE,
    YoutubeSearchIE.ie_key(): YoutubeSearchIE,
    YoutubeSearchURLIE.ie_key(): YoutubeSearchURLIE,
    YoutubeShortsAudioPivotIE.ie_key(): YoutubeShortsAudioPivotIE,
    YoutubeSubscriptionsIE.ie_key(): YoutubeSubscriptionsIE,
    YoutubeTabIE.ie_key(): YoutubeTabIE,
    YoutubeTruncatedIDIE.ie_key(): YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE.ie_key(): YoutubeTruncatedURLIE,
    YoutubeWatchLaterIE.ie_key(): YoutubeWatchLaterIE,
    YoutubeWebArchiveIE.ie_key(): YoutubeWebArchiveIE, # Assuming its ie_key() is 'WebArchiveYoutube' or similar
                                                       # Original key might be 'web.archive:youtube'
    YoutubeYtBeIE.ie_key(): YoutubeYtBeIE, # Its ie_key() is likely 'YoutubeYtBe'
    YoutubeYtUserIE.ie_key(): YoutubeYtUserIE,

    # Generic Extractor
    GenericIE.ie_key(): GenericIE, # Its ie_key() is 'Generic'
}

# The _ALL_CLASSES list is what yt-dlp iterates over to find a suitable extractor.
# It should contain the CLASS OBJECTS themselves, not strings.
_ALL_CLASSES = [
    # KinjaEmbedIE, # if kept
    # PeerTubeIE, # if kept
    # PeerTubePlaylistIE, # if kept
    YoutubeIE, # Most important
    YoutubePlaylistIE,
    YoutubeClipIE,
    YoutubeConsentRedirectIE,
    YoutubeFavouritesIE,
    YoutubeHistoryIE,
    YoutubeLivestreamEmbedIE,
    YoutubeMusicSearchURLIE,
    YoutubeNotificationsIE,
    YoutubeRecommendedIE,
    YoutubeSearchDateIE,
    YoutubeSearchIE,
    YoutubeSearchURLIE,
    YoutubeShortsAudioPivotIE,
    YoutubeSubscriptionsIE,
    YoutubeTabIE,
    YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE,
    YoutubeWatchLaterIE,
    YoutubeWebArchiveIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
    GenericIE, # Fallback
]

# This function is called by yt-dlp to get the list of all extractors.
def _real_extractors():
    return _ALL_CLASSES

# Optional: If you want to try and mimic the very original structure slightly more for Nuitka
# you could define all the IE classes you *removed* as simple pass-throughs to GenericIE
# or make them raise NotImplementedError. This is generally not needed if _ALL_CLASSES is minimal.

# Example of how the original file dynamically built _ALL_CLASSES (DO NOT INCLUDE THIS PART, just for info)
# _ALL_CLASSES = [klass for name, klass in globals().items() if name.endswith('IE') and name != 'GenericIE']
# _ALL_CLASSES.append(GenericIE) # Ensure GenericIE is last

# --- END OF FILE ---