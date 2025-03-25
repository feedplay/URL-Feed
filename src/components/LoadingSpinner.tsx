// components/LoadingSpinner.tsx
import React from 'react';

type SpinnerSize = 'small' | 'medium' | 'large';

interface LoadingSpinnerProps {
    size?: SpinnerSize;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'medium' }) => {
    const sizes: Record<SpinnerSize, string> = {
        small: '20px',
        medium: '40px',
        large: '60px'
    };

    const spinnerSize = sizes[size]; // ✅ No more TypeScript error

    const spinnerStyle = {
        width: spinnerSize,
        height: spinnerSize,
        border: '4px solid rgba(0, 0, 0, 0.1)',
        borderLeftColor: '#333',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
    };

    return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <div style={spinnerStyle}></div>
            <style>
                {`
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `}
            </style>
        </div>
    );
};

export default LoadingSpinner;
