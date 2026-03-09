import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { CookieConsentProvider } from './contexts/CookieConsentContext';
import { Layout } from './components/layout/Layout';
import { CookieConsentBanner } from './components/ui/CookieConsentBanner';
import ErrorBoundary from './components/ErrorBoundary';
import { hideKeyboard, useKeyboardScrollFix } from './hooks/useKeyboard';
import { useDeepLinks } from './hooks/useDeepLinks';
import { isNativePlatform } from './utils/platform';
import { HomePage, UploadPage, CreateRecipePage, RecipesPage, RecipeDetailPage, RecipeGroupDetailPage, CookbooksPage, CookbookDetailPage, SourcesPage, SourceDetailPage, UserPage, OrdersPage, VerifyEmailPage, VerifyEmailSentPage, ForgotPasswordPage, ResetPasswordPage } from './pages';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { EditProfilePage } from './pages/EditProfilePage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { AccountSettingsPage } from './pages/AccountSettingsPage';
import { PublicUserPage } from './pages/PublicUserPage';
import { CookbookPurchaseSuccessPage } from './pages/CookbookPurchaseSuccessPage';
import { CreateCookbookPage } from './pages/CreateCookbookPage';
import CopyrightPolicyPage from './pages/CopyrightPolicyPage';
import TermsOfServicePage from './pages/TermsOfServicePage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import NotFoundPage from './pages/NotFoundPage';

// Create a client
const queryClient = new QueryClient();

// Component to handle deep links (must be inside Router)
function DeepLinkHandler({ children }: { children: React.ReactNode }) {
  useDeepLinks();
  return <>{children}</>;
}

// Handle tap outside inputs to dismiss keyboard on iOS
const handleTapOutside = (e: React.MouseEvent) => {
  if (!isNativePlatform()) return;

  const target = e.target as HTMLElement;
  const isInteractiveElement =
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT' ||
    target.isContentEditable ||
    target.closest('input, textarea, select, [contenteditable="true"]');

  if (!isInteractiveElement) {
    hideKeyboard();
  }
};

function App() {
  // Enable keyboard scroll fix for iOS
  useKeyboardScrollFix();

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <CookieConsentProvider>
          <AuthProvider>
            <div onClick={handleTapOutside}>
              <Router>
                <DeepLinkHandler>
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
                    <Route path="/sources" element={<SourcesPage />} />
                    <Route path="/sources/:id" element={<SourceDetailPage />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/recipes/create" element={<CreateRecipePage />} />
                    <Route path="/orders" element={<OrdersPage />} />
                    <Route path="/profile" element={<UserPage />} />
                    <Route path="/profile/edit" element={<EditProfilePage />} />
                    <Route path="/profile/change-password" element={<ChangePasswordPage />} />
                    <Route path="/settings" element={<AccountSettingsPage />} />
                    <Route path="/users/:userId" element={<PublicUserPage />} />
                    <Route path="/users/by-username/:username" element={<PublicUserPage />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/verify-email" element={<VerifyEmailPage />} />
                    <Route path="/verify-email-sent" element={<VerifyEmailSentPage />} />
                    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                    <Route path="/reset-password" element={<ResetPasswordPage />} />
                    <Route path="/copyright-policy" element={<CopyrightPolicyPage />} />
                    <Route path="/terms-of-service" element={<TermsOfServicePage />} />
                    <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
                    {/* Catch-all route for 404 */}
                    <Route path="*" element={<NotFoundPage />} />
                  </Routes>
                </Layout>
                <CookieConsentBanner />
                </DeepLinkHandler>
              </Router>
            </div>
          </AuthProvider>
        </CookieConsentProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App
