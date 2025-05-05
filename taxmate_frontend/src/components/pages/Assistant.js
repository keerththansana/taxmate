import React, { useState, useRef, useEffect } from 'react';
import './Assistant.css';
import assistantImage from './Assistant.png';
import userImage from './User.jpg';
import axios from 'axios';

// Configure axios
axios.defaults.baseURL = 'http://localhost:8000';
axios.defaults.headers.common['Content-Type'] = 'application/json';

const Chatbot = () => {
    const [query, setQuery] = useState('');
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    // Update the scrollToBottom function to account for input container height
    const scrollToBottom = () => {
        if (messagesEndRef.current) {
            const inputContainer = document.querySelector('.assistant-input-container');
            const inputHeight = inputContainer?.getBoundingClientRect().height || 0;
            const scrollPosition = messagesEndRef.current.offsetTop - inputHeight - 20; // 20px buffer
            
            window.scrollTo({
                top: scrollPosition,
                behavior: 'smooth'
            });
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        try {
            setLoading(true);
            setMessages(prev => [...prev, { role: 'user', content: query }]);

            const response = await axios.post('/api/chatbot/chat/', { message: query }); // Changed from { query }

            if (response.data && response.data.success) {
                setMessages(prev => [...prev, { 
                    role: 'assistant', 
                    content: response.data.response 
                }]);
            }
        } catch (error) {
            console.error('Chatbot Error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "Sorry, I'm having trouble connecting right now. Please try again."
            }]);
        } finally {
            setLoading(false);
            setQuery('');
            if (textareaRef.current) {
                textareaRef.current.style.height = '24px'; // Reset to smaller height after submit
            }
        }
    };

    const handleInputChange = (e) => {
        setQuery(e.target.value);

        // Auto-grow textarea with smaller default height
        if (textareaRef.current) {
            textareaRef.current.style.height = '24px'; // Decreased default height
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
        }
    };

    return (
        <div className="assistant-container">
            <div className="chat-box">
                {messages.length === 0 ? (
                    <div className="welcome-container">
                        <div className="assistant-welcome">
                            <img src={assistantImage} alt="AI Assistant" className="assistant-image" />
                            <h1 className="assistant-title">Tax Assistant</h1>
                        </div>
                        <div className="empty-state">
                            <p>Hi! I am your tax Assistant. How can I help you today?</p>
                        </div>
                    </div>
                ) : (
                    messages.map((msg, index) => (
                        <div key={index} className={`chat-message ${msg.role}`}>
                            <img
                                alt={msg.role}
                                src={msg.role === 'user' ? userImage : assistantImage}
                                className="chat-avatar"
                            />
                            <div className="chat-bubble">
                                {msg.content}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            <form className="assistant-input-container" onSubmit={handleSubmit}>
                <textarea
                    ref={textareaRef}
                    value={query}
                    onChange={handleInputChange}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit(e);
                        }
                    }}
                    placeholder="Enter Your Questions Here..."
                    className="assistant-input"
                    rows={1}
                />
                <button 
                    type="submit" 
                    className="assistant-button" 
                    disabled={!query.trim() || loading}
                >
                    ↑
                </button>
            </form>
        </div>
    );
};

export default Chatbot;
