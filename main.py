import os
import gtts
import openai
import asyncio
import aiohttp
import soundfile
import speech_recognition as sr
from aiogram import Bot, Dispatcher, executor, types


bot_token = ""
api_key = ""

messages = {}
bot = Bot(token=bot_token)
openai.api_key = api_key
dp = Dispatcher(bot)
recognizer = sr.Recognizer()


async def echo_message(message, text):
    try:
        user_message = text
        username = message.from_user.username

        if username not in messages:
             messages[username] = []

        messages[username].append({"role": "user", "content": user_message})
        messages[username].append({"role": "system", "content": "You are a Helpful assistant."})

        should_respond = not message.reply_to_message or message.reply_to_message.from_user.id == bot.id

        if should_respond:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages[username],
                temperature=0.7,
                frequency_penalty=0.1,
                presence_penalty=0.1,
                user=username
            )
            chatgpt_response = completion.choices[0]['message']
            messages[username].append({"role": "assistant", "content": chatgpt_response['content']})
         
            return chatgpt_response['content']
    except Exception as e:
        await message.answer(e)
        await message.answer("Произошла ошибка при обработке запроса. Введите /start, чтобы перезапустить бота")


@dp.message_handler(commands=['voice'])
async def send_voice(message: types.Message):
    text = await echo_message(message, message.text)
    filename = message.from_user.username + str(message.message_id) + '.ogg'
   
    tts = gtts.gTTS(text=text, lang='ru')
    tts.save(filename)
    
    with open(filename, "rb") as audio:
        await bot.send_voice(message.chat.id, audio)
    
    os.remove(filename)


@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    try:
        username = message.from_user.username
    except AttributeError:
        await message.answer("Пожалуйста, укажите имя пользователя в настройках Telegram и повторите попытку.")
        return

    messages[username] = []
    await message.answer("Привет, я личный психолог Полины! Чтобы перезапустить бота пиши /start")


async def loading_animation(message: types.Message):
    animation = "|/-\\"
    idx = 0
    while True:
        await message.answer(animation[idx % len(animation)])
        await asyncio.sleep(0.1)
        idx += 1


@dp.message_handler(content_types=[types.ContentType.VOICE])
async def voice_message_handler(message: types.Message):
    file_id = message.voice.file_id
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path
    file_name = file_id + '.wav'

    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url) as response:
            if response.status == 200:
                content = await response.read()

                with open(file_name, "wb") as file:
                    file.write(content)

                data, samplerate = soundfile.read(file_name)
                soundfile.write(file_name, data, samplerate, subtype='PCM_16')

                try:
                    audio = sr.AudioFile(file_name)
                    with audio as source:
                        audio_data = recognizer.record(source)
                        text = recognizer.recognize_google(audio_data, language="ru-RU")
                        await message.answer(f"Ваш запрос: {text}")
                        os.remove(file_name)
                except sr.UnknownValueError:
                    await message.answer("Не удалось распознать речь.")
                except sr.RequestError as e:
                    await message.answer(f"Ошибка сервиса распознавания речи: {e}")
            else:
                await message.answer("Ошибка при скачивании голосового сообщения.")

        bot_text = await echo_message(message, text)
        await message.reply(bot_text, parse_mode='Markdown')


@dp.message_handler(content_types=[types.ContentType.TEXT])
async def text_message_handler(message: types.Message):
    bot_text = await echo_message(message, message.text)
    await message.reply(bot_text, parse_mode='Markdown')


if __name__ == '__main__':
    executor.start_polling(dp)