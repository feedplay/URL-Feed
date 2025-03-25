import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import Button from './Button';

const EmailInput: React.FC = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Function to validate email format
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    if (!email) {
      setError('Please enter your email');
      setIsSubmitting(false);
      return;
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await axios.post('http://localhost:4000/api/store-email', 
        { email },
        {
          headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          timeout: 5000, // 5 second timeout
        }
      );

      if (response.status === 201) {
        console.log('Email stored successfully:', response.data);
        navigate('/analysis', { 
          state: { 
            url: location.state?.url, 
            email, 
            emailStored: true 
          } 
        });
      } else {
        throw new Error('Failed to store email');
      }
    } catch (error: any) {
      console.error('❌ Complete Email Storage Error:', error);
      
      // More detailed error handling
      if (error.response) {
        // The request was made and the server responded with a status code
        setError(error.response.data.error || error.response.data.message || 'Failed to store email');
      } else if (error.request) {
        // The request was made but no response was received
        setError('No response from server. Please check your network connection.');
      } else {
        // Something happened in setting up the request
        setError('Error in sending request. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-xl shadow-lg">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Enter Your Email
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          To view your website's CRO analysis report
        </p>
        {location.state?.url && (
          <p className="mt-2 text-center text-sm text-gray-500">
            URL: {location.state.url}
          </p>
        )}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <input
              id="email"
              name="email"
              type="email"
              required
              className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {error && <div className="text-red-500 text-sm mt-2 text-center">{error}</div>}
          <Button 
            type="submit" 
            disabled={isSubmitting}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {isSubmitting ? 'Saving...' : 'See Report'}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default EmailInput;