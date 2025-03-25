import React, { useState, useEffect, useRef } from 'react';
import { X, Send, ChevronLeft, ChevronRight } from 'lucide-react';
import Button from './Button';

interface ChatDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialContext?: string;
  analysisCompleted: boolean;
  onRequestAnalysis?: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const ChatDialog: React.FC<ChatDialogProps> = ({
  open,
  onOpenChange,
  initialContext = '',
  analysisCompleted,
  onRequestAnalysis,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    { 
      role: 'assistant', 
      content: "Hello! I'm your CRO Assistant. How can I help you optimize your website's conversion rate today?"
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Reset messages when dialog is opened
  useEffect(() => {
    if (open) {
      // Only set initial context to input if it's a simple greeting or user question
      // Don't set it if it's a long text that looks like an assistant response
      if (initialContext && initialContext.length < 100 && !initialContext.includes('*')) {
        setInput(initialContext);
      } else {
        setInput('');
      }
    }
  }, [initialContext, open]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInput('');
    setLoading(true);
    
    try {
      // Call the API endpoint
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userMessage })
      });
      
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      
      const data = await response.json();
      
      if (data.response) {
        setMessages(prev => [
          ...prev, 
          { role: 'assistant', content: data.response }
        ]);
      } else if (data.error) {
        // Handle error in response
        setMessages(prev => [
          ...prev, 
          { role: 'assistant', content: `I'm having trouble connecting right now. Please try again in a moment.` }
        ]);
        console.error('Error from API:', data.error);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [
        ...prev, 
        { role: 'assistant', content: `I'm having trouble connecting right now. Please try again in a moment.` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;
  
  // Show analysis required message if analysis not completed
  if (!analysisCompleted) {
    return (
      <div className="fixed right-0 top-0 h-full bg-white shadow-lg z-50 w-96 flex flex-col">
        <div className="flex items-center justify-between border-b p-4">
          <h2 className="text-lg font-medium">CRO Assistant</h2>
          <button onClick={() => onOpenChange(false)} className="text-gray-500 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>
        
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="mb-4 text-gray-600">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-xl font-medium mb-2">Analysis Required</h3>
            <p className="mb-6">Please complete a website analysis before accessing the CRO Assistant.</p>
            {onRequestAnalysis && (
              <Button onClick={onRequestAnalysis} className="w-full">
                Start Website Analysis
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Render the collapsed toggle button when sidebar is collapsed
  if (collapsed) {
    return (
      <button 
        onClick={() => setCollapsed(false)}
        className="fixed right-0 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white p-2 rounded-l-md shadow-lg z-50"
      >
        <ChevronLeft size={24} />
      </button>
    );
  }

  return (
    <div className="fixed right-0 top-0 h-full bg-white shadow-lg z-50 w-96 flex flex-col">
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-lg font-medium">CRO Assistant</h2>
        <div className="flex items-center">
          <button 
            onClick={() => setCollapsed(true)}
            className="text-gray-500 hover:text-gray-700 mr-2"
          >
            <ChevronRight size={20} />
          </button>
          <button 
            onClick={() => onOpenChange(false)} 
            className="text-gray-500 hover:text-gray-700"
          >
            <X size={20} />
          </button>
        </div>
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div 
            key={index} 
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-[85%] p-3 rounded-lg ${
                message.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-tr-none' 
                  : 'bg-gray-100 text-gray-800 rounded-tl-none'
              }`}
            >
              <div className="prose prose-sm max-w-none">
                {message.content.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {line}
                    {i < message.content.split('\n').length - 1 && <br />}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 p-3 rounded-lg rounded-tl-none max-w-[80%]">
              <div className="flex space-x-2">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '600ms' }} />
              </div>
            </div>
          </div>
        )}
        
        {/* Reference for scrolling to bottom */}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about website optimization..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            <Send size={18} />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatDialog;