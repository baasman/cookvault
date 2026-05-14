import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { CookieConsentProvider } from './contexts/CookieConsentContext';
import { Layout } from './components/layout/Layout';
import { CookieConsentBanner } from './components/ui/CookieConsentBanner';
import { ErrorBoundary } from './components/ErrorBoundary';
import { hideKeyboard, useKeyboardScrollFix } from './hooks/useKeyboard';
import { useDeepLinks } from './hooks/useDeepLinks';
import { isNativePlatform } from './utils/platform';

// Lazy-loaded pages — each becomes its own chunk
const HomePage = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })));
const RecipesPage = lazy(() => import('./pages/RecipesPage').then(m => ({ default: m.RecipesPage })));
const RecipeDetailPage = lazy(() => import('./pages/RecipeDetailPage').then(m => ({ default: m.RecipeDetailPage })));
const RecipeGroupDetailPage = lazy(() => import('./pages/RecipeGroupDetailPage').then(m => ({ default: m.RecipeGroupDetailPage })));
const SmartFolderDetailPage = lazy(() => import('./pages/SmartFolderDetailPage').then(m => ({ default: m.SmartFolderDetailPage })));
const CookbooksPage = lazy(() => import('./pages/CookbooksPage').then(m => ({ default: m.CookbooksPage })));
const CookbookDetailPage = lazy(() => import('./pages/CookbookDetailPage').then(m => ({ default: m.CookbookDetailPage })));
const CreateCookbookPage = lazy(() => import('./pages/CreateCookbookPage').then(m => ({ default: m.CreateCookbookPage })));
const CookbookPurchaseSuccessPage = lazy(() => import('./pages/CookbookPurchaseSuccessPage').then(m => ({ default: m.CookbookPurchaseSuccessPage })));
const ProjectsListPage = lazy(() => import('./pages/ProjectsListPage').then(m => ({ default: m.ProjectsListPage })));
const CreateProjectPage = lazy(() => import('./pages/CreateProjectPage').then(m => ({ default: m.CreateProjectPage })));
const ProjectDashboardPage = lazy(() => import('./pages/ProjectDashboardPage').then(m => ({ default: m.ProjectDashboardPage })));
const SourcesPage = lazy(() => import('./pages/SourcesPage').then(m => ({ default: m.SourcesPage })));
const SourceDetailPage = lazy(() => import('./pages/SourceDetailPage').then(m => ({ default: m.SourceDetailPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then(m => ({ default: m.UploadPage })));
const CreateRecipePage = lazy(() => import('./pages/CreateRecipePage').then(m => ({ default: m.CreateRecipePage })));
const OrdersPage = lazy(() => import('./pages/OrdersPage').then(m => ({ default: m.OrdersPage })));
const UserPage = lazy(() => import('./pages/UserPage').then(m => ({ default: m.UserPage })));
const EditProfilePage = lazy(() => import('./pages/EditProfilePage').then(m => ({ default: m.EditProfilePage })));
const ChangePasswordPage = lazy(() => import('./pages/ChangePasswordPage').then(m => ({ default: m.ChangePasswordPage })));
const AccountSettingsPage = lazy(() => import('./pages/AccountSettingsPage').then(m => ({ default: m.AccountSettingsPage })));
const UpgradePage = lazy(() => import('./pages/UpgradePage').then(m => ({ default: m.UpgradePage })));
const PublicUserPage = lazy(() => import('./pages/PublicUserPage').then(m => ({ default: m.PublicUserPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage').then(m => ({ default: m.VerifyEmailPage })));
const VerifyEmailSentPage = lazy(() => import('./pages/VerifyEmailSentPage').then(m => ({ default: m.VerifyEmailSentPage })));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage').then(m => ({ default: m.ForgotPasswordPage })));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage').then(m => ({ default: m.ResetPasswordPage })));
const CopyrightPolicyPage = lazy(() => import('./pages/CopyrightPolicyPage').then(m => ({ default: m.CopyrightPolicyPage })));
const TermsOfServicePage = lazy(() => import('./pages/TermsOfServicePage').then(m => ({ default: m.TermsOfServicePage })));
const PrivacyPolicyPage = lazy(() => import('./pages/PrivacyPolicyPage').then(m => ({ default: m.PrivacyPolicyPage })));
const SupportPage = lazy(() => import('./pages/SupportPage').then(m => ({ default: m.SupportPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

// Loading fallback for lazy-loaded pages
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: '#f15f1c' }} />
    </div>
  );
}

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
                  <Suspense fallback={<PageLoader />}>
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/recipes" element={<RecipesPage />} />
                    <Route path="/recipes/:id" element={<RecipeDetailPage />} />
                    <Route path="/recipe-groups/:id" element={<RecipeGroupDetailPage />} />
                    <Route path="/smart-folders/:id" element={<SmartFolderDetailPage />} />
                    <Route path="/cookbooks" element={<CookbooksPage />} />
                    <Route path="/cookbooks/create" element={<CreateCookbookPage />} />
                    <Route path="/cookbooks/:id" element={<CookbookDetailPage />} />
                    <Route path="/cookbooks/:cookbookId/purchase-success" element={<CookbookPurchaseSuccessPage />} />
                    <Route path="/projects" element={<ProjectsListPage />} />
                    <Route path="/projects/create" element={<CreateProjectPage />} />
                    <Route path="/projects/:id" element={<ProjectDashboardPage />} />
                    <Route path="/sources" element={<SourcesPage />} />
                    <Route path="/sources/:id" element={<SourceDetailPage />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/recipes/create" element={<CreateRecipePage />} />
                    <Route path="/orders" element={<OrdersPage />} />
                    <Route path="/profile" element={<UserPage />} />
                    <Route path="/profile/edit" element={<EditProfilePage />} />
                    <Route path="/profile/change-password" element={<ChangePasswordPage />} />
                    <Route path="/settings" element={<AccountSettingsPage />} />
                    <Route path="/upgrade" element={<UpgradePage />} />
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
                    <Route path="/support" element={<SupportPage />} />
                    {/* Catch-all route for 404 */}
                    <Route path="*" element={<NotFoundPage />} />
                  </Routes>
                  </Suspense>
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

export { App }
