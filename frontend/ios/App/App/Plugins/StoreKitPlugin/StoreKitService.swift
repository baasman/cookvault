import StoreKit

/// Service for handling StoreKit 2 operations
actor StoreKitService {
    /// Product IDs for Cookle subscriptions
    private let productIds = ["com.cookle.app.premium.monthly"]

    /// Fetch available products from the App Store
    func fetchProducts() async throws -> [Product] {
        return try await Product.products(for: productIds)
    }

    /// Purchase a product by ID
    func purchase(productId: String) async throws -> Transaction {
        guard let product = try await Product.products(for: [productId]).first else {
            throw StoreError.productNotFound
        }

        let result = try await product.purchase()

        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            // Finish the transaction to acknowledge delivery
            await transaction.finish()
            return transaction
        case .userCancelled:
            throw StoreError.userCancelled
        case .pending:
            throw StoreError.pending
        @unknown default:
            throw StoreError.unknown
        }
    }

    /// Restore previous purchases
    func restorePurchases() async throws -> [Transaction] {
        var transactions: [Transaction] = []

        // Get all current entitlements (active subscriptions)
        for await result in Transaction.currentEntitlements {
            if let transaction = try? checkVerified(result) {
                transactions.append(transaction)
            }
        }

        return transactions
    }

    /// Get the active subscription if any
    func getActiveSubscription() async throws -> Transaction? {
        for await result in Transaction.currentEntitlements {
            if let transaction = try? checkVerified(result),
               transaction.productType == .autoRenewable {
                return transaction
            }
        }
        return nil
    }

    /// Check subscription status for a specific product
    func checkSubscriptionStatus(for productId: String) async throws -> Product.SubscriptionInfo.Status? {
        guard let product = try await Product.products(for: [productId]).first,
              let subscription = product.subscription else {
            return nil
        }

        let statuses = try await subscription.status
        return statuses.first
    }

    /// Verify a transaction result
    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified(_, let error):
            // StoreKit failed to verify the transaction
            throw StoreError.verificationFailed(error)
        case .verified(let safe):
            return safe
        }
    }
}

/// Errors that can occur during StoreKit operations
enum StoreError: LocalizedError {
    case productNotFound
    case userCancelled
    case pending
    case verificationFailed(Error)
    case unknown

    var errorDescription: String? {
        switch self {
        case .productNotFound:
            return "Product not found in the App Store"
        case .userCancelled:
            return "Purchase was cancelled by user"
        case .pending:
            return "Purchase is pending approval"
        case .verificationFailed(let error):
            return "Transaction verification failed: \(error.localizedDescription)"
        case .unknown:
            return "An unknown error occurred"
        }
    }
}
