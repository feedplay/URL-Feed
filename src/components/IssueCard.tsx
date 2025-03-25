import React from 'react';
import Button from './Button';

// Define the props interface with conversionImpact included
export interface IssueCardProps {
  title: string;
  description: string;
  impact: string;
  solution: string;
  conversionImpact?: string | number;
  onApplyFix: () => void;
  onLearnMore: () => void;
}

const IssueCard: React.FC<IssueCardProps> = ({
  title,
  description,
  impact,
  solution,
  conversionImpact,
  onApplyFix,
  onLearnMore
}) => {
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden border border-gray-100">
      <div className="p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">{title}</h3>
        
        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-1">Description</h4>
            <p className="text-sm text-gray-600">{description}</p>
          </div>
          
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-1">Impact</h4>
            <p className="text-sm text-gray-600">{impact}</p>
          </div>
          
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-1">Solution</h4>
            <p className="text-sm text-gray-600">{solution}</p>
          </div>
          
          {conversionImpact && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Potential Conversion Impact</h4>
              <div className="flex items-center">
                <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium">
                  {conversionImpact}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="bg-gray-50 px-6 py-3 flex space-x-3">
        <Button onClick={onApplyFix}>Apply Fix</Button>
        <Button variant="secondary" onClick={onLearnMore}>Learn More</Button>
      </div>
    </div>
  );
};

export default IssueCard;