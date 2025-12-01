# ZAYLON Web Interface

**AI-Powered Customer Engagement That Converts**

A stunning, production-ready web interface for the ZAYLON multi-agent system. Built with Next.js 14, TypeScript, and Tailwind CSS.

---

## Features

### Real-Time Agent Streaming
- Live chat interface with streaming responses
- Word-by-word response generation
- Typing indicators and smooth animations

### Complete Process Transparency
- **Process Visualization Panel**: See every step the AI takes in real-time
- **Analytics Dashboard**: Execution time, agent routing, tool usage metrics
- **System Logs Panel**: Terminal-style logs with millisecond precision

### Professional UI/UX
- Modern, clean design with smooth animations
- 60fps performance
- Mobile-responsive layout
- Dark mode system logs
- Gradient accents and professional color scheme

---

## Quick Start

### Prerequisites
- Node.js 18+ and npm
- ZAYLON backend running on `localhost:8000`

### Installation

```bash
# Navigate to web interface directory
cd zaylon-web

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your API key

# Run development server
npm run dev

# Visit http://localhost:3000
```

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your-secret-api-key
```

---

## Architecture

### Component Structure

```
src/
├── app/
│   ├── page.tsx              # Main page with all panels
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Global styles
├── components/
│   ├── ChatInterface.tsx           # Main chat window
│   ├── MessageBubble.tsx           # Individual messages
│   ├── ProcessVisualization.tsx    # Process flow panel
│   ├── AnalyticsDashboard.tsx      # Metrics display
│   ├── SystemLogsPanel.tsx         # Live logs
│   └── TypingIndicator.tsx
├── hooks/
│   └── useAgentStream.ts     # SSE streaming logic
├── lib/
│   ├── api.ts                # API client
│   └── utils.ts              # Utilities
└── types/
    └── agent.ts              # TypeScript types
```

### Data Flow

1. User sends message
2. `ChatInterface` calls `onMessageSend` prop
3. `useAgentStream` hook opens SSE connection
4. Stream chunks update:
   - `processSteps` state → ProcessVisualization
   - `logs` state → SystemLogsPanel
   - `analytics` state → AnalyticsDashboard
5. Final response renders in chat

---

## Component Details

### ChatInterface
- Manages conversation history
- Handles user input
- Displays messages with timestamps
- Shows typing indicator during streaming

### ProcessVisualization
- Real-time step tracking
- Status indicators (pending, active, completed, error)
- Execution time display
- Smooth animations

### AnalyticsDashboard
- Total execution time
- Agent used (Sales/Support)
- Tool calls count
- Thoughts count
- Visual metrics cards

### SystemLogsPanel
- Terminal-style interface
- Color-coded log levels (INFO, WARNING, ERROR)
- Auto-scroll with pause option
- Clear logs button
- Node information display

---

## Customization

### Colors

Edit `tailwind.config.js`:

```javascript
colors: {
  'zaylon-primary': '#6366f1',    // Main brand color
  'zaylon-secondary': '#8b5cf6',  // Secondary accent
  'zaylon-success': '#10b981',    // Success states
  'zaylon-warning': '#f59e0b',    // Warnings
  'zaylon-error': '#ef4444',      // Errors
}
```

### Animations

All animations use Framer Motion and Tailwind:
- `animate-slide-up`: Message bubbles
- `animate-fade-in`: Typing indicator
- `animate-pulse-soft`: Active process steps
- `hover:shadow-md`: Interactive elements

---

## Production Deployment

### Build for Production

```bash
npm run build
npm start
```

### Deploy to Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Configure environment variables in Vercel dashboard
```

### Deploy to Netlify

```bash
# Build command
npm run build

# Publish directory
.next

# Configure environment variables in Netlify dashboard
```

---

## Performance

- **60fps animations**: All transitions optimized
- **Lazy loading**: Components load on demand
- **Code splitting**: Automatic with Next.js
- **Image optimization**: Built-in Next.js optimization
- **Bundle size**: ~200KB gzipped

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Development Tips

### Hot Reload
Next.js automatically reloads on file changes

### TypeScript
All components are fully typed. Check `src/types/agent.ts` for API types.

### Debugging
1. Check browser console for errors
2. Inspect Network tab for SSE connection
3. Review System Logs panel for backend issues

### Adding New Features
1. Create component in `src/components/`
2. Add types to `src/types/agent.ts`
3. Update `page.tsx` to include component
4. Test with streaming endpoint

---

## Troubleshooting

### SSE Connection Fails
- Ensure backend is running on correct port
- Check CORS settings in backend
- Verify API key in `.env.local`

### Logs Not Appearing
- Check backend streaming endpoint
- Verify chunk type handling in `useAgentStream.ts`
- Inspect browser network tab

### Styling Issues
- Run `npm run build` to rebuild Tailwind
- Clear Next.js cache: `rm -rf .next`
- Check for conflicting CSS

---

## License

Created by Abdelrahman Abouroumia (Romia) & Abdelrahman Mashaal

---

## Support

For issues or questions:
1. Check `ZAYLON_IMPLEMENTATION_STATUS.md` in root
2. Review backend logs
3. Inspect browser console
4. Test API endpoint directly with curl

---

**Status**: Production Ready
**Version**: 1.0.0
**Last Updated**: 2025-12-01
