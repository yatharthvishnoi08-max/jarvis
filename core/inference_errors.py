from openai import APITimeoutError, APIConnectionError


def retryable(error):
    return isinstance(error, (APITimeoutError, APIConnectionError, TimeoutError, ConnectionError)) or getattr(error, 'status_code', None) in (404, 408, 429, 500, 502, 503, 504)


def user_message(error, actions_attempted=False):
    status = getattr(error, 'status_code', None)
    if isinstance(error, (APITimeoutError, TimeoutError)):
        message = 'The AI service took too long to answer. Please try again.'
    elif isinstance(error, (APIConnectionError, ConnectionError)):
        message = 'I lost the connection to the AI service. Please try again in a moment.'
    elif status == 429:
        message = 'The AI service is at its usage limit. Please try again shortly.'
    elif status in (401, 403):
        message = 'The AI service rejected its credentials. The provider connection needs attention.'
    else:
        message = 'I could not complete this request because the AI service returned an error.'
    return message + (' Some actions were already attempted; check Activity before retrying to avoid duplicates.'
                      if actions_attempted else ' No computer actions ran in this turn.')
