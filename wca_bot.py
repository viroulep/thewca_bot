#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Simple Bot to reply to Telegram messages.

This program is dedicated to the public domain under the CC0 license.

This Bot uses the Updater class to handle the bot.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic inline bot example. Applies different text transformations.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
from uuid import uuid4

from collections import defaultdict
import json
import logging
import os
import requests

from telegram import InlineQueryResultArticle, Update, ParseMode, \
    InputTextMessageContent
from telegram.ext import CallbackContext, Updater, InlineQueryHandler, CommandHandler

DELEGATE_STATUSES = {
    "trainee_delegate": "Trainee Delegate",
    "candidate_delegate": "Junior Delegate",
    "delegate": "Delegate",
    "senior_delegate": "Senior Delegate",
}

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

WCA_REGS_DATA = []
with open("data/wca-regulations.json", encoding="utf-8") as regs:
    WCA_REGS_DATA = json.load(regs)
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
WCA_BASE_URL = 'https://www.worldcubeassociation.org'
WCA_API_URL = f'{WCA_BASE_URL}/api/v0'
WCA_LOGO_URL = f'{WCA_BASE_URL}/files/WCAlogo_notext.svg'
REGIONAL_INDICATOR_OFFSET = 127397  # = ord("🇦") - ord("A")
HELP_TEXT = 'I only work inline, type my name (@thewca_bot) and search the WCA!'

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    _ = context
    update.message.reply_text(HELP_TEXT)


def bot_help(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    _ = context
    update.message.reply_text(HELP_TEXT)

def find_reg(text):
    """Find a given Regulation or Guideline in the json data we have"""
    result = "", "Couldn't find the Regulation or Guideline"
    for entry in WCA_REGS_DATA:
        if entry["id"] == text:
            result = entry["url"], entry["content_html"]
            break
    return result

def regulation_description(reg_type, reg):
    """Constructs a Regulation or Guideline description."""
    return (
        f'<a href="{WCA_BASE_URL}{reg["url"]}">{reg_type} {reg["id"]}</a>:\n'
        f'{reg["content_html"]}'
    )

def flag_from_iso2(iso2):
    """Returns an emoticon flag for the given iso2."""
    return "".join([chr(ord(x) + REGIONAL_INDICATOR_OFFSET) for x in iso2])

def profile_description(person):
    """Constructs a person profile description."""
    delegate = (
        f'This person is a {DELEGATE_STATUSES[person["delegate_status"]]}'
        f' for {person["region"]}.\n' if person["delegate_status"] else ''
        )
    teams = [(
        f'{team["friendly_id"].upper()} team '
        f'{"leader" if team["leader"] else "member"}.\n'
    ) for team in person["teams"]]
    return (
        f'{person["name"]} ({person["wca_id"]}) - {flag_from_iso2(person["country_iso2"])}\n'
        f'{delegate}'
        f'{"".join(teams)}'
        f'[WCA profile]({person["url"]})'
    )

def competition_description(comp):
    """Constructs a competition description."""
    delegates = [f'[{person["name"]}]({person["url"]})' for person in comp["delegates"]]
    organizers = [f'[{person["name"]}]({person["url"]})' for person in comp["organizers"]]
    return (
          f'{comp["name"]} ({comp["id"]}) - {flag_from_iso2(comp["country_iso2"])}\n'
          f'Competition starts on {comp["start_date"]} and ends on {comp["end_date"]}\n'
          f'Page on the [WCA website]({comp["url"]})\n'
          f'Delegate(s): {", ".join(delegates)}\n'
          f'Organizer(s): {", ".join(organizers)}\n'
    )

def handle_person(person):
    """Return a Person search result."""
    return InlineQueryResultArticle(
        id=str(uuid4()),
        title=f'{person["name"]}\'s profile',
        thumb_url=person["avatar"]["thumb_url"],
        url=person["url"],
        input_message_content=InputTextMessageContent(
            profile_description(person),
            parse_mode=ParseMode.MARKDOWN),
        description=flag_from_iso2(person["country_iso2"]),
    )

def handle_competition(competition):
    """Return a Competition search result."""
    return InlineQueryResultArticle(
        id=str(uuid4()),
        title=competition["name"],
        url=competition["url"],
        thumb_url=WCA_LOGO_URL,
        input_message_content=InputTextMessageContent(
            competition_description(competition),
            parse_mode=ParseMode.MARKDOWN),
        description=(
            f'Competition, starts {competition["start_date"]} in '
            f'{competition["city"]}, {flag_from_iso2(competition["country_iso2"])}'),
    )

def handle_regulation(reg):
    """Return a Regulation search result."""
    reg_type = "Guideline" if reg["id"].endswith("+") else "Regulation"
    return InlineQueryResultArticle(
        id=str(uuid4()),
        title=f'{reg_type} {reg["id"]}',
        url=f'{WCA_BASE_URL}{reg["url"]}',
        thumb_url=WCA_LOGO_URL,
        input_message_content=InputTextMessageContent(
            regulation_description(reg_type, reg),
            parse_mode=ParseMode.HTML),
        description=f'{reg["content_html"][:20]} ...',
    )

def default_handler(item):
    """Default handler in case the item is not supported (eg: posts)"""
    _ = item

HANDLERS = defaultdict(lambda: default_handler)
HANDLERS["person"] = handle_person
HANDLERS["competition"] = handle_competition
HANDLERS["regulation"] = handle_regulation

def handle_result(result):
    """Call the appropriate handler for the given result."""
    return HANDLERS[result["class"]](result)

def omni_search(text):
    """Consults the WCA omnisearch and returns an array of results."""
    params = dict(q=text)
    if len(text) <= 2:
        return []
    resp = requests.get(url=f'{WCA_API_URL}/search', params=params, timeout=5)
    data = json.loads(resp.text)

    return list(filter(lambda x: x is not None, map(handle_result, data["result"])))

def inlinequery(update: Update, context: CallbackContext) -> None:
    """Handle the inline query."""
    _ = context
    query = update.inline_query.query
    if len(query) <= 2:
        return
    results = omni_search(query)
    update.inline_query.answer(results)


def error(update: object, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    logger.error('Update "%s" caused error "%s"', update_str, context.error)


def main() -> None:
    """The main entry point ;)"""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", bot_help))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(InlineQueryHandler(inlinequery))

    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
