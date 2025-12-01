'use client';

import { useState, useRef, useEffect } from 'react';
import { v4 as uuid } from 'uuid';
import { Message } from '@/types/agent';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { Send } from 'lucide-react';

interface ChatInterfaceProps {
  onMessageSend: (message: string, onResponse: (response: string) => void) => void;
  isStreaming: boolean;
}

export function ChatInterface({ onMessageSend, isStreaming }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [currentAssistantId, setCurrentAssistantId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: uuid(),
      content: input.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');

    // Create placeholder assistant message
    const assistantId = uuid();
    setCurrentAssistantId(assistantId);

    const assistantMessage: Message = {
      id: assistantId,
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      streaming: true,
    };

    setMessages(prev => [...prev, assistantMessage]);

    // Stream response
    onMessageSend(userMessage.content, (response) => {
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, content: response, streaming: false }
            : m
        )
      );
      setCurrentAssistantId(null);
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-zaylon-primary to-zaylon-secondary">
        <h2 className="text-xl font-bold text-white">ZAYLON AI Agent</h2>
        <p className="text-sm text-blue-100">Your intelligent e-commerce assistant</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-lg font-medium mb-2">Welcome to ZAYLON</p>
              <p className="text-sm">Ask me about products, orders, or policies!</p>
            </div>
          </div>
        )}

        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isStreaming && currentAssistantId && (
          <TypingIndicator />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about products, orders, or policies..."
            disabled={isStreaming}
            className="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-zaylon-primary focus:border-transparent outline-none disabled:bg-gray-100 disabled:cursor-not-allowed transition-all"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="px-6 py-3 bg-zaylon-primary text-white rounded-lg hover:bg-zaylon-secondary transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Powered by GPT-4 • Multi-agent architecture • Press Enter to send
        </p>
      </div>
    </div>
  );
}
