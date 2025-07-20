import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { RecipeGroupDetail } from '../components/recipe/RecipeGroupDetail';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui';

const RecipeGroupDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const groupId = id ? parseInt(id, 10) : null;

  if (!isAuthenticated) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Please log in to view this recipe group
        </h2>
        <Button onClick={() => navigate('/login')}>
          Sign In
        </Button>
      </div>
    );
  }

  if (!groupId) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4" style={{color: '#1c120d'}}>
          Invalid recipe group
        </h2>
        <Button onClick={() => navigate('/recipes?filter=groups')}>
          Back to All Groups
        </Button>
      </div>
    );
  }

  return <RecipeGroupDetail groupId={groupId} />;
};

export { RecipeGroupDetailPage };