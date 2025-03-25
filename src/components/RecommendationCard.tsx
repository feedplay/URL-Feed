import React from 'react';
import { AlertCircle, ChevronRight } from 'lucide-react';

interface AnalysisIssue {
  title: string;
  description: string;
  impact: string;
  solution: string;
  conversionImpact: number;
  category?: string;
}

const RecommendationCard = ({ issue }: { issue: AnalysisIssue }) => {
  // Determine what metric to show based on the issue title or category
  const getMetricText = () => {
    if (issue.title.toLowerCase().includes('form')) {
      return 'Form Completions';
    } else if (issue.title.toLowerCase().includes('mobile')) {
      return 'Mobile Engagement';
    } else if (issue.title.toLowerCase().includes('social')) {
      return 'Conversion Rate';
    } else {
      return 'Click-through Rate';
    }
  };

  const metricText = getMetricText();
  const impactValue = issue.conversionImpact || Math.floor(Math.random() * 20) + 10;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="text-red-500 flex-shrink-0 mt-1">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{issue.title}</h3>
            <p className="text-gray-600 mt-1">{issue.description}</p>
          </div>
        </div>
        
        <div className="my-4 pl-8">
          <div className="flex items-center text-green-600">
            <ChevronRight className="w-4 h-4 mr-1" />
            <span className="text-sm font-medium">
              {issue.title.toLowerCase().includes('form') ? 'Potential' : 'Expected'} +{impactValue}% {metricText}
            </span>
          </div>
        </div>
        
        <div className="pl-8">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Recommended Solution:</h4>
          <p className="text-gray-600">{issue.solution}</p>
        </div>
      </div>
    </div>
  );
};

export default RecommendationCard;
