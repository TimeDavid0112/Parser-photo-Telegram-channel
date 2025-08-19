import os
import re
import requests
from bs4 import BeautifulSoup
from pyrogram import Client
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

from config import API_ID, API_HASH, SESSION_NAME, DOWNLOAD_DIR

console = Console()


def download_from_telegraph(url, save_dir, stats):
    """Скачивает картинки со страницы telegra.ph"""
    try:
        r = requests.get(url)
        r.raise_for_status()
    except Exception as e:
        console.log(f"[red]Ошибка при скачивании {url}: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if src.startswith("/"):
            src = "https://telegra.ph" + src
        try:
            img_data = requests.get(src).content
            fname = os.path.join(save_dir, os.path.basename(src.split("?")[0]))
            with open(fname, "wb") as f:
                f.write(img_data)
            stats["files"] += 1
            console.log(f"[green]Скачано:[/green] {fname}")
        except Exception as e:
            console.log(f"[red]Ошибка скачивания {src}: {e}")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not href.startswith("http"):
            continue
        if "telegra.ph" in href:
            if href.startswith("/"):
                href = "https://telegra.ph" + href
            download_from_telegraph(href, save_dir, stats)


TELEGRAPH_REGEX = re.compile(r"^https?://(www\.)?telegra\.ph/[\w\-%/]+", re.IGNORECASE)


def extract_telegraph_links(msg) -> list[str]:
    """Достаёт ВСЕ telegraph-ссылки из текста, гиперссылок и кнопок"""
    links = []

    if msg.text:
        for word in msg.text.split():
            if TELEGRAPH_REGEX.match(word):
                links.append(word)

    if msg.caption:
        for word in msg.caption.split():
            if TELEGRAPH_REGEX.match(word):
                links.append(word)

    if msg.entities:
        for ent in msg.entities:
            if ent.url and TELEGRAPH_REGEX.match(ent.url):
                links.append(ent.url)

    if msg.caption_entities:
        for ent in msg.caption_entities:
            if ent.url and TELEGRAPH_REGEX.match(ent.url):
                links.append(ent.url)

    if msg.reply_markup and msg.reply_markup.inline_keyboard:
        for row in msg.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url and TELEGRAPH_REGEX.match(btn.url):
                    links.append(btn.url)

    return list(set(links))


def backup_channel_photos(client, channel_id, limit):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    chat = client.get_chat(channel_id)
    console.log(f"[green]Подключен к каналу:[/green] {chat.title} (id={chat.id})")

    messages = list(client.get_chat_history(chat.id, limit=limit))

    stats = {"files": 0}

    with Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Загрузка...", total=len(messages))

        for msg in reversed(messages):
            if msg.photo:
                path = client.download_media(msg.photo, file_name=DOWNLOAD_DIR)
                stats["files"] += 1
                console.log(f"[cyan]Фото сохранено:[/cyan] {path}")

            if msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
                path = client.download_media(msg.document, file_name=DOWNLOAD_DIR)
                stats["files"] += 1
                console.log(f"[cyan]Фото (документ) сохранено:[/cyan] {path}")

            telegraph_links = extract_telegraph_links(msg)
            for url in telegraph_links:
                console.log(f"[yellow]Нашёл Telegraph-ссылку:[/yellow] {url}")
                download_from_telegraph(url, DOWNLOAD_DIR, stats)

            progress.update(task, advance=1)

    console.print(f"[bold green]Готово! Скачано файлов: {stats['files']}[/bold green]")


if __name__ == "__main__":
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

    with app:
        table = Table(title="Telegram Backup", style="bold white on black")
        table.add_column("Параметр", style="cyan")
        table.add_column("Описание", style="green")

        table.add_row("Channel ID", "Укажи ID канала (@channel или -100xxxx)")
        table.add_row("Limit", "Сколько сообщений скачать (снизу вверх)")

        console.print(table)

        ch_id = console.input("[bold cyan]Введи ID канала:[/bold cyan] ")

        total_msgs = app.get_chat_history_count(ch_id)

        console.print(f"[magenta]Всего сообщений в канале:[/magenta] {total_msgs}")

        limit = int(console.input("[bold cyan]Сколько сообщений скачать?:[/bold cyan] "))

        if limit > total_msgs:
            console.print(f"[yellow]В канале только {total_msgs} сообщений. Скачиваю все.[/yellow]")
            limit = total_msgs

        backup_channel_photos(app, ch_id, limit)