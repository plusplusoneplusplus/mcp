import asyncio
import platform
from server.tools import load_tasks_from_yaml, executor

async def test_tasks():
    """Test the task abstraction layer with OS-conditional commands"""
    print("Testing task abstraction layer with OS-conditional commands...")
    
    # Get current OS
    os_type = platform.system().lower()
    print(f"Current OS: {os_type}")
    
    # Load available tasks
    tasks = load_tasks_from_yaml()
    print(f"Found {len(tasks)} predefined tasks:")
    
    os_compatible_tasks = []
    
    for name, task in tasks.items():
        # Check if task has OS-conditional commands
        if 'commands' in task:
            # Check if it supports current OS
            if os_type in task['commands']:
                command = task['commands'][os_type]
                os_compatible_tasks.append(name)
                print(f"- {name}: {task.get('description')} (OS-specific command for {os_type}: {command})")
            else:
                print(f"- {name}: {task.get('description')} (Not compatible with {os_type})")
        elif 'command' in task:
            # Simple command
            command = task.get('command')
            os_compatible_tasks.append(name)
            print(f"- {name}: {task.get('description')} (Generic command: {command})")
        else:
            print(f"- {name}: {task.get('description')} (Warning: No command defined)")

    # Select tasks to test
    tasks_to_test = []
    
    # Try to find system info, network info, and process list tasks
    for task_type in ['system_info', 'network_info', 'process_list']:
        if task_type in os_compatible_tasks:
            tasks_to_test.append(task_type)
    
    # Execute each selected task
    for task_name in tasks_to_test:
        print(f"\n\nExecuting task: {task_name}")
        task = tasks[task_name]
        
        # Get the appropriate command for the current OS
        if 'commands' in task:
            command = task['commands'][os_type]
        else:
            command = task.get('command', '')
            
        timeout = task.get('timeout')
        
        # Execute the command asynchronously
        print(f"Starting command: {command}")
        result = await executor.execute_async(command, timeout)
        token = result["token"]
        print(f"Command started with token: {token}")
        
        # Wait a brief moment
        print("Waiting 1 second before checking status...")
        await asyncio.sleep(1)
        
        # Check status without waiting for completion
        status = await executor.query_process(token, wait=False)
        print(f"Status after 1 second: {status.get('status')}")
        
        # Wait for completion and get results
        print("Waiting for completion...")
        final_result = await executor.query_process(token, wait=True)
        print(f"Task completed with success: {final_result.get('success')}")
        
        # Print output preview
        output = final_result.get('output', '')
        preview_length = min(200, len(output))
        print(f"Output preview ({preview_length} characters of {len(output)} total):")
        print(output[:preview_length] + "..." if len(output) > preview_length else output)
        
        # Check we can retrieve the output again without waiting
        print("\nRetrieving output again without waiting...")
        cached_result = await executor.query_process(token, wait=False)
        print(f"Cached result status: {cached_result.get('status')}")
        print(f"Output length: {len(cached_result.get('output', ''))}")
    
    print("\nTask abstraction test with OS-conditional commands completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_tasks()) 