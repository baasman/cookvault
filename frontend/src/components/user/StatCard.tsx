import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  color?: string;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon, 
  color = '#f15f1c' 
}) => {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 transition-all duration-200 hover:shadow-md" style={{borderColor: '#e8d7cf'}}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-text-secondary mb-1">{title}</h3>
          <div className="text-2xl font-bold text-text-primary">{value}</div>
          {subtitle && (
            <p className="text-sm text-text-secondary mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="ml-4 flex-shrink-0">
            <div 
              className="w-12 h-12 rounded-lg flex items-center justify-center"
              style={{backgroundColor: `${color}15`, color: color}}
            >
              {icon}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export { StatCard };