import React from 'react';

interface LoadingSpinnerProps {
    size?: 'small' | 'medium' | 'large';
    text?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps? = ({
    size = 'medium',
    text,
}) => {
    return (
    <div className={`spinner spinner-${size}`}>
      <div className="spinner-ring" />
      {text && <p>{text}</p>}
    </div>
  );
}