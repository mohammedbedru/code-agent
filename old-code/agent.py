# from pathlib import Path

# from ollama import chat

# from tools import (
#     list_files,
#     read_file,
#     search_code
# )

# from prompts import SYSTEM_PROMPT


# MODEL = "llama3.2:3b"


# def main():

#     print("=" * 60)
#     print("Local Coding Agent")
#     print("=" * 60)

#     project_directory = input(
#         "\nEnter project directory: "
#     ).strip()

#     project_path = Path(
#         project_directory
#     ).resolve()

#     if not project_path.exists():

#         print(
#             "\nERROR: Project directory "
#             "does not exist."
#         )

#         return

#     # --------------------------------------------------
#     # Project-specific tool wrappers
#     # --------------------------------------------------

#     def list_project_files():

#         return list_files(
#             str(project_path)
#         )

#     def read_project_file(
#         file_path: str,
#         start_line: int = None,
#         end_line: int = None
#     ):

#         print(
#             f"\n📖 Reading: {file_path}"
#         )

#         if (
#             start_line is not None
#             or end_line is not None
#         ):

#             print(
#                 f"   Lines: "
#                 f"{start_line or 1}"
#                 f"-"
#                 f"{end_line or 'end'}"
#             )

#         full_path = (
#             project_path
#             / file_path
#         )

#         return read_file(
#             str(full_path),
#             start_line,
#             end_line
#         )

#     def search_project_code(
#         query: str
#     ):

#         print(
#             f"\n🔎 Searching for: "
#             f"{query}"
#         )

#         result = search_code(
#             str(project_path),
#             query
#         )

#         print(
#             f"\n🔎 Search result:"
#         )

#         print(
#             result
#         )

#         return result

#     # --------------------------------------------------
#     # Tools available to the LLM
#     # --------------------------------------------------

#     tools = [

#         list_project_files,

#         read_project_file,

#         search_project_code,

#     ]

#     # --------------------------------------------------
#     # Conversation
#     # --------------------------------------------------

#     messages = [

#         {
#             "role": "system",

#             "content": SYSTEM_PROMPT
#         }

#     ]

#     print(
#         "\nProject loaded."
#     )

#     print(
#         "Type 'exit' to quit.\n"
#     )

#     # --------------------------------------------------
#     # Main conversation loop
#     # --------------------------------------------------

#     while True:

#         user_input = input(
#             "You: "
#         ).strip()

#         if user_input.lower() == "exit":

#             break

#         messages.append(

#             {
#                 "role": "user",

#                 "content": user_input

#             }

#         )

#         # --------------------------------------------------
#         # Agent loop
#         # --------------------------------------------------

#         while True:

#             print(
#                 "\nAgent is thinking...\n"
#             )

#             response = chat(

#                 model=MODEL,

#                 messages=messages,

#                 tools=tools

#             )

#             # --------------------------------------------------
#             # No tool call
#             # --------------------------------------------------

#             if not response.message.tool_calls:

#                 print(
#                     "Agent:"
#                 )

#                 print(
#                     response.message.content
#                 )

#                 messages.append(

#                     {

#                         "role": "assistant",

#                         "content":
#                         response.message.content

#                     }

#                 )

#                 break

#             # --------------------------------------------------
#             # Store assistant tool-call message
#             # --------------------------------------------------

#             messages.append(
#                 response.message
#             )

#             # --------------------------------------------------
#             # Execute tools
#             # --------------------------------------------------

#             for tool_call in (
#                 response.message.tool_calls
#             ):

#                 function_name = (
#                     tool_call.function.name
#                 )

#                 arguments = (
#                     tool_call.function.arguments
#                 )

#                 print(
#                     f"🔧 Tool: "
#                     f"{function_name}"
#                 )

#                 # ------------------------------------------
#                 # LIST FILES
#                 # ------------------------------------------

#                 if function_name == (
#                     "list_project_files"
#                 ):

#                     result = (
#                         list_project_files()
#                     )

#                 # ------------------------------------------
#                 # READ FILE
#                 # ------------------------------------------

#                 elif function_name == (
#                     "read_project_file"
#                 ):

#                     file_path = (
#                         arguments.get(
#                             "file_path"
#                         )
#                     )

#                     start_line = (
#                         arguments.get(
#                             "start_line"
#                         )
#                     )

#                     end_line = (
#                         arguments.get(
#                             "end_line"
#                         )
#                     )

#                     print(
#                         f"   file_path: "
#                         f"{file_path}"
#                     )

#                     result = (
#                         read_project_file(

#                             file_path,

#                             start_line,

#                             end_line

#                         )
#                     )

#                 # ------------------------------------------
#                 # SEARCH CODE
#                 # ------------------------------------------

#                 elif function_name == (
#                     "search_project_code"
#                 ):

#                     query = (
#                         arguments.get(
#                             "query"
#                         )
#                     )

#                     print(
#                         f"   query: "
#                         f"{query}"
#                     )

#                     result = (
#                         search_project_code(
#                             query
#                         )
#                     )

#                 # ------------------------------------------
#                 # UNKNOWN TOOL
#                 # ------------------------------------------

#                 else:

#                     result = (

#                         f"ERROR: Unknown tool "
#                         f"{function_name}"

#                     )

#                 # ------------------------------------------
#                 # Return result to model
#                 # ------------------------------------------

#                 messages.append(

#                     {

#                         "role": "tool",

#                         "content": result

#                     }

#                 )

#         print()


# if __name__ == "__main__":

#     main()