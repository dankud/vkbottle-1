from vkbottle import Bot, AnswerObject

bot = Bot('my-token', 1, debug=True, asyncio=True)
admin_id = 1  # VK Group admin ID


@bot.on_message_undefined()
def who_i_am(answer):
    answer('I work only in chats')


@bot.on_message_chat('bot')
def i_am_here(answer):
    answer('[id{user:id}|{user:first_name}], i am here!')


if __name__ == "__main__":
    bot.run()