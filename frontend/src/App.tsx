import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { Layout } from './components/layout/Layout';
import { HomePage, UploadPage, CreateRecipePage, RecipesPage, RecipeDetailPage, RecipeGroupDetailPage, CookbooksPage, CookbookDetailPage, UserPage, OrdersPage, VerifyEmailPage, VerifyEmailSentPage } from './pages';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { EditProfilePage } from './pages/EditProfilePage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { PublicUserPage } from './pages/PublicUserPage';
import { CookbookPurchaseSuccessPage } from './pages/CookbookPurchaseSuccessPage';
import { CreateCookbookPage } from './pages/CreateCookbookPage';
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
              <Route path="/cookbooks/create" element={<CreateCookbookPage />} />
              <Route path="/cookbooks/:id" element={<CookbookDetailPage />} />
              <Route path="/cookbooks/:cookbookId/purchase-success" element={<CookbookPurchaseSuccessPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/recipes/create" element={<CreateRecipePage />} />
              <Route path="/orders" element={<OrdersPage />} />
              <Route path="/profile" element={<UserPage />} />
              <Route path="/profile/edit" element={<EditProfilePage />} />
              <Route path="/profile/change-password" element={<ChangePasswordPage />} />
              <Route path="/users/:userId" element={<PublicUserPage />} />
              <Route path="/users/by-username/:username" element={<PublicUserPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/verify-email" element={<VerifyEmailPage />} />
              <Route path="/verify-email-sent" element={<VerifyEmailSentPage />} />
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
