"""Shared LLM plumbing: the OpenRouter client, prompt loading, and translation.

OpenRouter exposes an OpenAI-compatible API, so we talk to it through the OpenAI
SDK - the same pattern as the sample program from the week 4 exercise. The API
key is read from the environment and never hard-coded.
"""

import json
import os

from openai import OpenAI

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'

# Free OpenRouter models are rate-limited and frequently overloaded upstream, so we
# walk this chain in order instead of depending on any single model.
DEFAULT_MODELS = [
    'inclusionai/ling-3.0-flash-sante:free',
    'nvidia/nemotron-3-super-120b-a12b:free',
    'qwen/qwen3.8-27b:free',
    'z-ai/glm-5.2:free',
]

# Repository root, so prompts/ resolves no matter where the app is launched from.
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PROMPT_DIR = os.path.join(ROOT_DIR, 'prompts')


class LLMError(RuntimeError):
    """Raised when the LLM call fails or its response cannot be used."""


def get_models():
    """Models to try, in order. OPENROUTER_MODELS (comma-separated) overrides."""
    configured = os.getenv('OPENROUTER_MODELS') or os.getenv('OPENROUTER_MODEL')
    if configured:
        return [name.strip() for name in configured.split(',') if name.strip()]
    return list(DEFAULT_MODELS)


def _describe_error(response):
    """Extract the error body from a response that arrived without any choices.

    OpenRouter answers HTTP 200 with `choices: None` plus an `error` field when the
    upstream provider is overloaded, so this never raises and cannot be caught.
    """
    detail = getattr(response, 'error', None)
    if detail is None and getattr(response, 'model_extra', None):
        detail = response.model_extra.get('error')
    return str(detail) if detail else 'empty response'


def call_llm_model(messages, model=None, temperature=0.2):
    """Send a chat completion request to OpenRouter and return the reply text.

    Pass `model` to pin one model (the probe script does this); leave it unset to walk
    the fallback chain.
    """
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        raise LLMError('OPENROUTER_API_KEY is not set')

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
    models = [model] if model else get_models()

    failures = []
    for name in models:
        try:
            response = client.chat.completions.create(
                model=name,
                messages=messages,
                temperature=temperature,
            )
        except Exception as exc:
            # Auth, network and rate-limit errors all surface here.
            failures.append(f'{name}: {exc}')
            continue

        content = response.choices[0].message.content if response.choices else None
        if content:
            return content
        failures.append(f'{name}: {_describe_error(response)}')

    raise LLMError('All models failed -> ' + ' | '.join(failures))


def load_prompt(filename):
    """Read a prompt template from the prompts/ directory."""
    with open(os.path.join(PROMPT_DIR, filename), encoding='utf-8') as fh:
        return fh.read()


def _parse_json_object(raw):
    """Parse a JSON object out of a model reply, tolerating ``` fences."""
    text = raw.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else ''
        text = text.rsplit('```', 1)[0]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some models wrap the JSON in prose - retry with the outermost braces.
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise LLMError(f'Model did not return valid JSON: {raw[:200]}')


def translate_note(title, content, target_language):
    """Translate a note's title and content.

    Returns {'title': ..., 'content': ...}. The template is filled with str.replace
    rather than str.format because the prompt body contains literal braces.
    """
    system_prompt = load_prompt('translate_prompt.md').replace(
        '{target_language}', target_language
    )
    messages = [
        {'role': 'system', 'content': system_prompt},
        {
            'role': 'user',
            'content': json.dumps({'title': title, 'content': content}, ensure_ascii=False),
        },
    ]

    result = _parse_json_object(call_llm_model(messages))
    if not isinstance(result, dict):
        raise LLMError('Model returned JSON that is not an object')

    return {
        'title': result.get('title') or title,
        'content': result.get('content') or content,
    }
