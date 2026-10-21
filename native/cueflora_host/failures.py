"""Allowlisted failure metadata. Never include provider bodies, URLs or keys."""
STAGES = {'credentials', 'download', 'audio-preparation', 'upload', 'transcription', 'translation',
          'update-check', 'update-download', 'native-connection', 'unknown'}
CODES = {'credential-unavailable', 'transport-policy', 'download-failed', 'audio-preparation-failed',
         'provider-auth', 'provider-permission', 'provider-payment', 'provider-rate-limit',
         'provider-request', 'provider-unavailable', 'network', 'timeout', 'cancelled',
         'invalid-response', 'verification-failed', 'helper-unavailable', 'unknown'}


class OperationFailure(RuntimeError):
    def __init__(self, stage, code, http_status=None):
        if stage not in STAGES or code not in CODES:
            raise ValueError('Invalid failure classification')
        self.detail = {'stage': stage, 'code': code}
        if http_status is not None:
            if type(http_status) is not int or not 400 <= http_status <= 599:
                raise ValueError('Invalid failure HTTP status')
            self.detail['httpStatus'] = http_status
        super().__init__('Operation failed: ' + code + (f' (HTTP {http_status})' if http_status else ''))


def http_failure(stage, status):
    if type(status) is not int or not 400 <= status <= 599:
        return OperationFailure(stage, 'invalid-response')
    code = {400: 'provider-request', 401: 'provider-auth', 402: 'provider-payment',
            403: 'provider-permission', 404: 'provider-request', 405: 'provider-request',
            413: 'provider-request', 415: 'provider-request', 422: 'provider-request',
            429: 'provider-rate-limit'}.get(status, 'provider-unavailable' if status >= 500 else 'provider-request')
    return OperationFailure(stage, code, status)
