import logging
import re
import json
import openai
from typing import List
from loguru import logger

from app.config import config

openai_api_key = config.app.get("openai_api_key")
if not openai_api_key:
    raise ValueError("openai_api_key is not set, please set it in the config.toml file.")

openai_model_name = config.app.get("openai_model_name")
if not openai_model_name:
    raise ValueError("openai_model_name is not set, please set it in the config.toml file.")

openai_base_url = config.app.get("openai_base_url")

openai.api_key = openai_api_key
openai_model_name = openai_model_name
if openai_base_url:
    openai.base_url = openai_base_url


def _generate_response(prompt: str) -> str:
    model_name = openai_model_name

    response = openai.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
    ).choices[0].message.content
    return response


def generate_script(video_subject: str, language: str = "zh-CN", paragraph_number: int = 1) -> str:
    prompt = f"""
# Role: Video Script Generator

## Goals:
Generate a script for a video, depending on the subject of the video.

## Constrains:
1. the script is to be returned as a string with the specified number of paragraphs.
2. do not under any circumstance reference this prompt in your response.
3. get straight to the point, don't start with unnecessary things like, "welcome to this video".
4. you must not include any type of markdown or formatting in the script, never use a title. 
5. only return the raw content of the script. 
6. do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line. 
7. you must not mention the prompt, or anything about the script itself. also, never talk about the amount of paragraphs or lines. just write the script.

## Output Example:
What is the meaning of life. This question has puzzled philosophers.

# Initialization:
- video subject: {video_subject}
- output language: {language}
- number of paragraphs: {paragraph_number}
""".strip()

    final_script = ""
    logger.info(f"subject: {video_subject}")
    logger.debug(f"prompt: \n{prompt}")
    response = _generate_response(prompt=prompt)

    # Return the generated script
    if response:
        # Clean the script
        # Remove asterisks, hashes
        response = response.replace("*", "")
        response = response.replace("#", "")

        # Remove markdown syntax
        response = re.sub(r"\[.*\]", "", response)
        response = re.sub(r"\(.*\)", "", response)

        # Split the script into paragraphs
        paragraphs = response.split("\n\n")

        # Select the specified number of paragraphs
        selected_paragraphs = paragraphs[:paragraph_number]

        # Join the selected paragraphs into a single string
        final_script = "\n\n".join(selected_paragraphs)

        # Print to console the number of paragraphs used
        # logger.info(f"number of paragraphs used: {len(selected_paragraphs)}")
    else:
        logging.error("gpt returned an empty response")

    logger.success(f"completed: \n{final_script}")
    return final_script


def generate_terms(video_subject: str, video_script: str, amount: int = 5) -> List[str]:
    prompt = f"""
# Role: Video Search Terms Generator

## Goals:
Generate {amount} search terms for stock videos, depending on the subject of a video.

## Constrains:
1. the search terms are to be returned as a json-array of strings.
2. each search term should consist of 1-3 words, always add the main subject of the video.
3. you must only return the json-array of strings. you must not return anything else. you must not return the script.
4. the search terms must be related to the subject of the video.
5. reply with english search terms only.

## Output Example:
["search term 1", "search term 2", "search term 3","search term 4","search term 5"]

## Context:
### Video Subject
{video_subject}

### Video Script
{video_script}
""".strip()

    logger.info(f"subject: {video_subject}")
    logger.debug(f"prompt: \n{prompt}")
    response = _generate_response(prompt)
    search_terms = []

    try:
        search_terms = json.loads(response)
        if not isinstance(search_terms, list) or not all(isinstance(term, str) for term in search_terms):
            raise ValueError("response is not a list of strings.")

    except (json.JSONDecodeError, ValueError):
        # logger.warning(f"gpt returned an unformatted response. attempting to clean...")
        # Attempt to extract list-like string and convert to list
        match = re.search(r'\["(?:[^"\\]|\\.)*"(?:,\s*"[^"\\]*")*\]', response)
        if match:
            try:
                search_terms = json.loads(match.group())
            except json.JSONDecodeError:
                logger.error(f"could not parse response: {response}")
                return []

    logger.success(f"completed: \n{search_terms}")
    return search_terms


if __name__ == "__main__":
    video_subject = "生命的意义是什么"
    script = generate_script(video_subject=video_subject, language="zh-CN", paragraph_number=1)
    # print("######################")
    # print(script)
    search_terms = generate_terms(video_subject=video_subject, video_script=script, amount=5)
    # print("######################")
    # print(search_terms)
