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

import re, json

from telegram.utils.helpers import escape_markdown

from telegram import InlineQueryResultArticle, ParseMode, \
  InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

wca_regs_data = json.load(open("wca-regulations.json"))
telegram_token = os.environ['TELEGRAM_TOKEN']

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
  """Send a message when the command /start is issued."""
  update.message.reply_text('Please input a WCA Regulation or Guideline and I\'ll give you its text.')


def help(bot, update):
  """Send a message when the command /help is issued."""
  update.message.reply_text('Please input a WCA Regulation or Guideline and I\'ll give you its text.')

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


def inlinequery(bot, update):
  """Handle the inline query."""
  query = update.inline_query.query
  url, message = find_reg(query)
  results = [
      InlineQueryResultArticle(
          id=uuid4(),
          title="Search result",
          input_message_content=InputTextMessageContent(
            query + ": " + message)),
      ]
  update.inline_query.answer(results)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
  # Create the Updater and pass it your bot's token.
  updater = Updater(token=telegram_token)

  logger.warning('Token is "%s"', telegram_token)

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
