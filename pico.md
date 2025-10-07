Pico is a note taking + personal assistant app, powered by AI. 

Functionality:
* Note taking: it allows users to take notes for meetings, thoughts on a particular topic, add images etc. Just like a google doc or the apple note app.
* Personal assistant: it supports users to talk to an AI assitant, who has access to all the notes taken before, and a sets of tools to analyze, sythesize information, like chatGPT. 


Usecase Examples:
* I have regular 1:1 with Nikola, before the meeting, I check with Pico, who provides me suggestions of topics, based on our previous 1:1 and my todo list
* I can write my thoughts on a particular problem, drafting a potential solution, and ask Pico right there for critical feedbacks, without having to leave the app. I ended up create a better solution. 
* I can take notes in chronological order, one topic at a time or by meetings. Pico can help me to organize them by topics, so if I want to look at what has happened on a particular topic, it's right there for me. 
* Pico check my notes for todos, if spot one, it automatically add them to the todo list. 
* After taking notes from a meeting, pico can help me to generate a summary with clear TODO and owneres to share. 
* Smart reminders: Remind me to review this post before that meeting 


UI:
* Minimalist UI
* The main window for note taking, it's just a plain text editor with no fancy functionality 
  * the main window can support tabs
  * the "note" tab is the main tab, which is always open, it saves to a regular text file.
  * more tabs can be create, either by user or Pico, then can also be saved or as a temporoy view. 
* Right panel is to chat with Pico 
* Left panel has a todo list 


Platform:
* Pico runs on MacOS
* Pico are mainly used by tech savy users, so it can be built using cmd
* Please use python as the backend engine, unless there is a strong reason not to
* For frontend use language that's most suitable for the task, the key is it needs to be snappy and sleek looking 
* For LLM, please use Claude, I have already provided the access token in .env file

Backend Architecture:
* the backend are composed of pico_agent and plugin class. 
* pico_agent class is the main chat surface user is interacting with, it's responsible for 
  * understanding user need through chat
  * interact with plugins through reading from them and writing into them 
* plugin class are extensible classes that implements note, todo and possibly other widgets which contains content. It should support
  * functions that allow pico_agent to read it's content 
  * functions that allow pico_agent to add/remove/update it's content 
* pico_agent interact with plugins using MCP protocol
  * plugins expose their API to a MCP server 
  * pico_agent discover, understand and interate with those API through a MCP client 