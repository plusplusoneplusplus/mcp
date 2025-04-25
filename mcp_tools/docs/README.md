# MCP Tools Documentation

This directory contains documentation for the MCP Tools system.

## Available Documentation

- [Creating Custom Tools](creating_tools.md) - Learn how to create and register new tools for the system
- [Dependency Injection](dependency_injection.md) - Understand how the dependency injection system works

## System Overview

MCP Tools is a plugin-based system that provides a framework for creating and using various tools for development, automation, and integration tasks. The system is designed to be:

- **Modular**: Each tool is a separate component that can be used independently
- **Extensible**: New tools can be easily added by implementing the appropriate interfaces
- **Discoverable**: Tools are automatically discovered and registered
- **Composable**: Tools can use other tools through dependency injection

## Key Components

- **ToolInterface**: The base interface that all tools must implement
- **Plugin System**: Handles tool registration and discovery
- **Dependency Injector**: Manages dependencies between tools
- **Specialized Interfaces**: Extended interfaces for specific types of tools
- **Core Tools**: Built-in tools that provide common functionality

## Getting Started

If you're new to MCP Tools, start by reading the [Creating Custom Tools](creating_tools.md) guide to understand how to create and use tools in the system. Then, learn about tool dependencies in the [Dependency Injection](dependency_injection.md) guide. 