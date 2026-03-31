import Capacitor
import StoreKit

/// Capacitor plugin for StoreKit 2 In-App Purchases
@objc(StoreKitPlugin)
public class StoreKitPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "StoreKitPlugin"
    public let jsName = "StoreKit"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "getProducts", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "purchase", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "restorePurchases", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getActiveSubscription", returnType: CAPPluginReturnPromise)
    ]

    private let storeKitService = StoreKitService()

    /// Fetch available products from the App Store
    @objc func getProducts(_ call: CAPPluginCall) {
        Task {
            do {
                let products = try await storeKitService.fetchProducts()
                let productData = products.map { product -> [String: Any] in
                    return [
                        "id": product.id,
                        "displayName": product.displayName,
                        "description": product.description,
                        "price": product.price.description,
                        "displayPrice": product.displayPrice
                    ]
                }
                call.resolve(["products": productData])
            } catch {
                call.reject("Failed to fetch products: \(error.localizedDescription)")
            }
        }
    }

    /// Purchase a product
    @objc func purchase(_ call: CAPPluginCall) {
        guard let productId = call.getString("productId") else {
            call.reject("Product ID is required")
            return
        }

        Task {
            do {
                let verified = try await storeKitService.purchase(productId: productId)

                call.resolve([
                    "success": true,
                    "transactionId": String(verified.transaction.id),
                    "originalTransactionId": String(verified.transaction.originalID),
                    "productId": verified.transaction.productID,
                    "jwsRepresentation": verified.jwsRepresentation
                ])
            } catch let error as StoreError {
                switch error {
                case .userCancelled:
                    call.reject("Purchase cancelled", "USER_CANCELLED")
                case .pending:
                    call.reject("Purchase pending", "PENDING")
                case .productNotFound:
                    call.reject("Product not found", "PRODUCT_NOT_FOUND")
                case .verificationFailed:
                    call.reject("Verification failed", "VERIFICATION_FAILED")
                case .unknown:
                    call.reject("Unknown error", "UNKNOWN")
                }
            } catch {
                call.reject("Purchase failed: \(error.localizedDescription)")
            }
        }
    }

    /// Restore previous purchases
    @objc func restorePurchases(_ call: CAPPluginCall) {
        Task {
            do {
                let verifiedTransactions = try await storeKitService.restorePurchases()
                let transactionData = verifiedTransactions.map { verified -> [String: Any] in
                    return [
                        "transactionId": String(verified.transaction.id),
                        "originalTransactionId": String(verified.transaction.originalID),
                        "productId": verified.transaction.productID,
                        "jwsRepresentation": verified.jwsRepresentation
                    ]
                }
                call.resolve(["transactions": transactionData])
            } catch {
                call.reject("Failed to restore purchases: \(error.localizedDescription)")
            }
        }
    }

    /// Get the currently active subscription
    @objc func getActiveSubscription(_ call: CAPPluginCall) {
        Task {
            do {
                if let verified = try await storeKitService.getActiveSubscription() {
                    // Format expiration date
                    var expirationDateString = ""
                    if let expirationDate = verified.transaction.expirationDate {
                        let formatter = ISO8601DateFormatter()
                        expirationDateString = formatter.string(from: expirationDate)
                    }

                    call.resolve([
                        "hasActiveSubscription": true,
                        "productId": verified.transaction.productID,
                        "expirationDate": expirationDateString,
                        "originalTransactionId": String(verified.transaction.originalID),
                        "jwsRepresentation": verified.jwsRepresentation
                    ])
                } else {
                    call.resolve(["hasActiveSubscription": false])
                }
            } catch {
                call.reject("Failed to check subscription: \(error.localizedDescription)")
            }
        }
    }
}
