import discord, os
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
from dateutil import parser
import asyncio

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Connect to SQLite database
conn = sqlite3.connect('tasks_events.db')
c = conn.cursor()

# Create tables for tasks and events if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (id INTEGER PRIMARY KEY, user TEXT, task TEXT, completed BOOLEAN)''')

c.execute('''CREATE TABLE IF NOT EXISTS events
             (id INTEGER PRIMARY KEY, user TEXT, event TEXT, event_time TEXT, notified BOOLEAN)''')
conn.commit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Command to add a task
@bot.command()
async def add_task(ctx, *, task):
    c.execute("INSERT INTO tasks (user, task, completed) VALUES (?, ?, ?)",
              (str(ctx.author), task, False))
    conn.commit()
    await ctx.send(f'Task "{task}" added!')

# Command to list tasks
@bot.command()
async def list_tasks(ctx):
    c.execute("SELECT id, task, completed FROM tasks WHERE user=? AND completed=0", (str(ctx.author),))
    tasks = c.fetchall()
    if tasks:
        response = "Your tasks:\n"
        for task in tasks:
            response += f"{task[0]}. {task[1]}\n"
        await ctx.send(response)
    else:
        await ctx.send("You have no tasks!")

# Command to mark a task as completed
@bot.command()
async def complete_task(ctx, task_id: int):
    c.execute("UPDATE tasks SET completed = 1 WHERE id = ? AND user = ?", (task_id, str(ctx.author)))
    conn.commit()
    await ctx.send(f'Task {task_id} marked as completed!')

# Command to remove a task
@bot.command()
async def remove_task(ctx, task_id: int):
    c.execute("DELETE FROM tasks WHERE id = ? AND user = ?", (task_id, str(ctx.author)))
    conn.commit()
    await ctx.send(f'Task {task_id} removed!')

# Command to add an event
@bot.command()
async def add_event(ctx, event_name, event_time):
    try:
        event_time = parser.parse(event_time)
        c.execute("INSERT INTO events (user, event, event_time, notified) VALUES (?, ?, ?, ?)",
                  (str(ctx.author), event_name, event_time.isoformat(), False))
        conn.commit()
        await ctx.send(f'Event "{event_name}" scheduled for {event_time}.')
    except ValueError:
        await ctx.send("Invalid date format. Please use a format like '2024-08-23 14:30'.")

# Command to list events
@bot.command()
async def list_events(ctx):
    c.execute("SELECT id, event, event_time FROM events WHERE user=? AND notified=0", (str(ctx.author),))
    events = c.fetchall()
    if events:
        response = "Your upcoming events:\n"
        for event in events:
            event_time = datetime.fromisoformat(event[2])
            response += f"{event[0]}. {event[1]} - {event_time.strftime('%Y-%m-%d %H:%M')}\n"
        await ctx.send(response)
    else:
        await ctx.send("You have no upcoming events!")

# Command to remove an event
@bot.command()
async def remove_event(ctx, event_id: int):
    c.execute("DELETE FROM events WHERE id = ? AND user = ?", (event_id, str(ctx.author)))
    conn.commit()
    await ctx.send(f'Event {event_id} removed!')

# Function to notify users of upcoming events
@tasks.loop(minutes=1)
async def check_events():
    current_time = datetime.now()
    c.execute("SELECT id, user, event, event_time FROM events WHERE notified=0")
    events = c.fetchall()

    for event in events:
        event_time = datetime.fromisoformat(event[3])
        # Notify 10 minutes before the event
        if event_time - timedelta(minutes=10) <= current_time <= event_time:
            user = await bot.fetch_user(event[1])
            await user.send(f"Reminder: Your event '{event[2]}' is starting at {event_time.strftime('%Y-%m-%d %H:%M')}!")
            c.execute("UPDATE events SET notified = 1 WHERE id = ?", (event[0],))
            conn.commit()

@check_events.before_loop
async def before_check_events():
    await bot.wait_until_ready()

check_events.start()

# Pomodoro timer
@bot.command()
async def pomodoro(ctx, work_time: int = 25, break_time: int = 5):
    await ctx.send(f"Starting Pomodoro: {work_time} minutes work, {break_time} minutes break.")
    await asyncio.sleep(work_time * 60)
    await ctx.send("Time to take a break!")
    await asyncio.sleep(break_time * 60)
    await ctx.send("Break over, back to work!")

# Start the bot
bot.run('TOKEN')
