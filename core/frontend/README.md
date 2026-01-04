# @tma-platform/core

Reusable frontend infrastructure package providing core functionality for building web apps with Telegram Mini App support.

## What's Inside

This package contains platform-agnostic, reusable components and utilities for web applications:

### Platform Abstractions
- **Platform API**: Unified interface for Telegram SDK and web platform
- **Telegram Utilities**: `useTelegram`, `usePlatform`, `usePlatformMock`
- **Mock Support**: Testing and development without Telegram environment

### UI Components
- **Layouts**: `BaseLayout`, `DesktopLayout`, `TabsLayout`
- **Components**: `AppButton`, `MainButton`, `SecondaryButton`, `BottomPopup`, `Placeholder`, `Steps`, `ExtraFooter`
- Telegram-native UI patterns and styling

### API Integration
- **API Client**: Type-safe API client with OpenAPI support
- **Authentication**: Automatic Telegram authentication handling
- Platform detection and configuration

### Composables
- **Navigation**: `useNavigation` for routing
- **Language**: `useLanguage` for i18n integration
- **Layout**: `useLayout` for responsive layouts
- **Scroll**: `useScroll` for scroll management
- **Placeholder**: `usePlaceholderHeight` for dynamic sizing

### Services
- **Static Assets**: `useStatic` for asset management
- **Lottie**: `useLottie` for animations

### Analytics
- **PostHog Integration**: Analytics and feature flags
- Event tracking and user behavior

### Utilities
- **DOM**: DOM manipulation helpers
- **Date**: Date formatting and localization
- **Number**: Number formatting utilities
- **Color**: Color manipulation helpers

### Types
- **Language Service**: Interface for language management
- **Injection Keys**: Vue dependency injection keys

## Usage

```typescript
// Import from package root
import {
  usePlatform,
  useTelegram,
  BaseLayout,
  AppButton,
  useNavigation,
  useLanguage,
  apiClient,
  usePostHog
} from '@tma-platform/core';

// Use in your components
const platform = usePlatform();
const { mainButton, backButton } = useTelegram();
const { navigate } = useNavigation();
```

## Installation

This package is part of the TMA Platform monorepo and is consumed by apps in the workspace:

```json
{
  "dependencies": {
    "@tma-platform/core": "workspace:*"
  }
}
```

## Development

This package is designed to be framework-agnostic and can be extracted to new web app projects. The core layer should never import from app-specific code.

## Architecture

The core package follows clean architecture principles:
- **Platform Layer**: Telegram SDK abstractions
- **UI Layer**: Reusable components and layouts
- **API Layer**: Type-safe HTTP clients
- **Composables Layer**: Reusable Vue composition functions
- **Services Layer**: Infrastructure services
- **Utils Layer**: Pure utility functions

All exports are available through the main package entry point (`@tma-platform/core`).
