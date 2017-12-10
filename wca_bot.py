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

import re, json, os, requests

from telegram.utils.helpers import escape_markdown

from telegram import InlineQueryResultArticle, ParseMode, \
  InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

wca_regs_data = json.load(open("data/wca-regulations.json"))
telegram_token = os.environ['TELEGRAM_TOKEN']
wca_base_url = 'https://www.worldcubeassociation.org'
wca_api_url = wca_base_url + '/api/v0'
wca_logo_url = wca_base_url + '/files/WCAlogo_notext.svg'

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
  """Send a message when the command /start is issued."""
  update.message.reply_text('I only work inline, type my name and search the WCA!')


def help(bot, update):
  """Send a message when the command /help is issued."""
  update.message.reply_text('I only work inline, type my name and search the WCA!')

def get_regs(bot, update):
  url, message = find_reg(update.message.text)
  bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)

def find_reg(text):
  result = "", "Couldn't find the Regulation or Guideline"
  for entry in wca_regs_data:
    if entry["id"] == text:
      result = entry["url"], entry["content_html"]
      break
  return result

def regulation_description(reg_type, reg):
  description = "<a href=\"{}\">{} {}</a>:\n".format(wca_base_url+reg["url"], reg_type, reg["id"])
  description += reg["content_html"]
  logger.info(description)
  return description

def profile_description(person):
  description = "{} ({}) - {}\n".format(person["name"], person["wca_id"], person["country_iso2"])
  if person["delegate_status"]:
    description += "This person is a {} for {}\n".format(person["delegate_status"].replace("_", " "), person["region"])
  for team in person["teams"]:
    description += "{} team member.\n".format(team["friendly_id"])
  description += "[WCA profile]({})".format(person["url"])
  logger.info(description)
  return description

def competition_description(comp):
  description = "{} ({}) - {}\n".format(comp["name"], comp["id"], comp["country_iso2"])
  description += "Competition starts on {} and ends on {}\n".format(comp["start_date"], comp["end_date"])
  delegates = []
  for person in comp["delegates"]:
    delegates.append("[{}]({})".format(person["name"], person["url"]))
  description += "Delegate(s): " + ", ".join(delegates) + "\n"
  organizers = []
  for person in comp["organizers"]:
    organizers.append("[{}]({})".format(person["name"], person["url"]))
  description += "Organizer(s): " + ", ".join(organizers)
  description += "Page on the [WCA website]({})".format(comp["url"])
  logger.info(description)
  return description

def omni_search(text):
  params = dict(q=text)
  if len(text) <= 2:
    return []
  resp = requests.get(url=wca_api_url+"/search", params=params)
  data = json.loads(resp.text)
  results = []

  for result in data["result"]:
    if result["class"] == "person":
      results.append(InlineQueryResultArticle(
          id=uuid4(),
          title="{}'s profile".format(result["name"]),
          thumb_url=result["avatar"]["thumb_url"],
          url=result["url"],
          input_message_content=InputTextMessageContent(profile_description(result), parse_mode=ParseMode.MARKDOWN),
          description=result["country_iso2"],
        ))
    elif result["class"] == "competition":
      results.append(InlineQueryResultArticle(
          id=uuid4(),
          title=result["name"],
          url=result["url"],
          thumb_url=wca_logo_url,
          input_message_content=InputTextMessageContent(competition_description(result), parse_mode=ParseMode.MARKDOWN),
          description="Competition, starts {} in {}, {}".format(result["start_date"], result["city"], result["country_iso2"]),
        ))
    elif result["class"] == "regulation":
      reg_type = "Guideline" if result["id"].endswith("+") else "Regulation"
      results.append(InlineQueryResultArticle(
          id=uuid4(),
          title="{} {}".format(reg_type, result["id"]),
          url=wca_base_url+result["url"],
          thumb_url=wca_logo_url,
          input_message_content=InputTextMessageContent(regulation_description(reg_type, result), parse_mode=ParseMode.HTML),
          description="{} ...".format(result["content_html"][:20]),
        ))
  return results


def inlinequery(bot, update):
  """Handle the inline query."""
  query = update.inline_query.query
  results = omni_search(query)
  update.inline_query.answer(results)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
  # Create the Updater and pass it your bot's token.
  updater = Updater(token=telegram_token)

  # Get the dispatcher to register handlers
  dp = updater.dispatcher

  # on different commands - answer in Telegram
  dp.add_handler(CommandHandler("start", start))
  dp.add_handler(CommandHandler("help", help))

  # dp.add_handler(MessageHandler(Filters.text, get_regs))
  # on noncommand i.e message - echo the message on Telegram
  dp.add_handler(InlineQueryHandler(inlinequery))

  # log all errors
  dp.add_error_handler(error)

  # Start the Bot
  updater.start_polling()

  # Block until the user presses Ctrl-C or the process receives SIGINT,
  # SIGTERM or SIGABRT. This should be used most of the time, since
  # start_polling() is non-blocking and will stop the bot gracefully.
  updater.idle()


if __name__ == '__main__':
  main()
