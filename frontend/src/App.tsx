import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { Layout } from './components/layout/Layout';
import { HomePage, UploadPage, CreateRecipePage, RecipesPage, RecipeDetailPage, RecipeGroupDetailPage, CookbooksPage, CookbookDetailPage, UserPage } from './pages';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import CopyrightPolicyPage from './pages/CopyrightPolicyPage';
import TermsOfServicePage from './pages/TermsOfServicePage';

// Create a client
const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/recipes" element={<RecipesPage />} />
              <Route path="/recipes/:id" element={<RecipeDetailPage />} />
              <Route path="/recipe-groups/:id" element={<RecipeGroupDetailPage />} />
              <Route path="/cookbooks" element={<CookbooksPage />} />
              <Route path="/cookbooks/:id" element={<CookbookDetailPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/recipes/create" element={<CreateRecipePage />} />
              <Route path="/profile" element={<UserPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/copyright-policy" element={<CopyrightPolicyPage />} />
              <Route path="/terms-of-service" element={<TermsOfServicePage />} />
            </Routes>
          </Layout>
      </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App
