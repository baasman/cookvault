import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  TruckIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { apiFetch } from '../utils/apiInterceptor';
import { getApiUrl } from '../utils/getApiUrl';
import { formatDateShort } from '../utils/formatters';

interface PrintOrder {
  id: number;
  order_number: string;
  status: string;
  cookbook_title?: string;
  cookbook_id?: number;
  quantity: number;
  total_cost: number;
  created_at: string;
  updated_at: string;
  shipping_name?: string;
  shipping_address_line1?: string;
  shipping_city?: string;
  shipping_state_code?: string;
  shipping_postal_code?: string;
  specification?: {
    trim_size: string;
    binding_type: string;
    paper_type: string;
    cover_finish: string;
    page_count: number;
    color_pages: boolean;
  };
}

interface OrdersResponse {
  orders: PrintOrder[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

const statusConfig = {
  DRAFT: {
    label: 'Draft',
    color: 'bg-gray-100 text-gray-800',
    icon: DocumentTextIcon
  },
  PENDING_PAYMENT: {
    label: 'Pending Payment',
    color: 'bg-yellow-100 text-yellow-800',
    icon: CurrencyDollarIcon
  },
  PAYMENT_FAILED: {
    label: 'Payment Failed',
    color: 'bg-red-100 text-red-800',
    icon: XCircleIcon
  },
  PAID: {
    label: 'Paid',
    color: 'bg-green-100 text-green-800',
    icon: CheckCircleIcon
  },
  SUBMITTED_TO_PRINTER: {
    label: 'Submitted to Printer',
    color: 'bg-blue-100 text-blue-800',
    icon: TruckIcon
  },
  PRINTING: {
    label: 'Printing',
    color: 'bg-indigo-100 text-indigo-800',
    icon: ClockIcon
  },
  SHIPPED: {
    label: 'Shipped',
    color: 'bg-purple-100 text-purple-800',
    icon: TruckIcon
  },
  DELIVERED: {
    label: 'Delivered',
    color: 'bg-emerald-100 text-emerald-800',
    icon: CheckCircleIcon
  },
  CANCELLED: {
    label: 'Cancelled',
    color: 'bg-gray-100 text-gray-800',
    icon: XCircleIcon
  },
  REFUNDED: {
    label: 'Refunded',
    color: 'bg-orange-100 text-orange-800',
    icon: ExclamationTriangleIcon
  }
};

export const OrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<PrintOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState<OrdersResponse['pagination'] | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    fetchOrders();
  }, [currentPage, statusFilter]);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: '10'
      });

      if (statusFilter) {
        params.append('status', statusFilter.toLowerCase());
      }

      const response = await apiFetch(`${getApiUrl()}/print-orders/?${params}`);

      if (response.ok) {
        const data: OrdersResponse = await response.json();
        setOrders(data.orders);
        setPagination(data.pagination);
      } else {
        throw new Error('Failed to fetch orders');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const config = statusConfig[status as keyof typeof statusConfig] || {
      label: status,
      color: 'bg-gray-100 text-gray-800',
      icon: DocumentTextIcon
    };

    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-4 h-4 mr-1" />
        {config.label}
      </span>
    );
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleStatusFilterChange = (status: string) => {
    setStatusFilter(status);
    setCurrentPage(1); // Reset to first page when filtering
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="bg-white p-6 rounded-lg shadow">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Print Orders</h1>
          <p className="mt-2 text-gray-600">Manage and track your cookbook print orders</p>
        </div>

        {/* Filters */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleStatusFilterChange('')}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                statusFilter === '' 
                  ? 'bg-emerald-100 text-emerald-800' 
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              All Orders
            </button>
            {Object.entries(statusConfig).map(([status, config]) => (
              <button
                key={status}
                onClick={() => handleStatusFilterChange(status)}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  statusFilter === status 
                    ? 'bg-emerald-100 text-emerald-800' 
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                {config.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <p className="text-red-600">{error}</p>
            <button
              onClick={fetchOrders}
              className="mt-2 text-red-600 hover:text-red-700 font-medium"
            >
              Try again
            </button>
          </div>
        )}

        {/* Orders List */}
        {orders.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No print orders found</h3>
            <p className="mt-2 text-gray-600">
              {statusFilter 
                ? `No orders with status "${statusConfig[statusFilter as keyof typeof statusConfig]?.label || statusFilter}"`
                : "You haven't placed any print orders yet."
              }
            </p>
            {!statusFilter && (
              <Link
                to="/cookbooks"
                className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700"
              >
                Browse Cookbooks
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <div key={order.id} className="bg-white rounded-lg shadow p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Order #{order.order_number}
                      </h3>
                      <StatusBadge status={order.status} />
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">Cookbook:</span>
                        {order.cookbook_title ? (
                          <Link
                            to={`/cookbooks/${order.cookbook_id}`}
                            className="block text-emerald-600 hover:text-emerald-700"
                          >
                            {order.cookbook_title}
                          </Link>
                        ) : (
                          <span className="block">Unknown cookbook</span>
                        )}
                      </div>
                      
                      <div>
                        <span className="font-medium">Quantity:</span>
                        <span className="block">{order.quantity} {order.quantity === 1 ? 'copy' : 'copies'}</span>
                      </div>
                      
                      <div>
                        <span className="font-medium">Total:</span>
                        <span className="block">{formatCurrency(order.total_cost)}</span>
                      </div>
                      
                      <div>
                        <span className="font-medium">Ordered:</span>
                        <span className="block">{formatDateShort(order.created_at)}</span>
                      </div>
                    </div>

                    {order.specification && (
                      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 bg-gray-50 p-3 rounded">
                        <div>
                          <span className="font-medium">Size:</span>
                          <span className="block">{order.specification.trim_size}</span>
                        </div>
                        <div>
                          <span className="font-medium">Binding:</span>
                          <span className="block">{order.specification.binding_type}</span>
                        </div>
                        <div>
                          <span className="font-medium">Paper:</span>
                          <span className="block">{order.specification.paper_type}</span>
                        </div>
                        <div>
                          <span className="font-medium">Pages:</span>
                          <span className="block">{order.specification.page_count}</span>
                        </div>
                      </div>
                    )}

                    {order.shipping_name && (
                      <div className="mt-4 text-sm text-gray-600">
                        <span className="font-medium">Shipping to:</span>
                        <div className="block">
                          {order.shipping_name}<br />
                          {order.shipping_address_line1}<br />
                          {order.shipping_city}, {order.shipping_state_code} {order.shipping_postal_code}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col space-y-2 ml-4">
                    <Link
                      to={`/orders/${order.id}`}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                      View Details
                    </Link>
                    
                    {order.status === 'DRAFT' && (
                      <button className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700">
                        Complete Order
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pagination && pagination.pages > 1 && (
          <div className="mt-8 flex items-center justify-between">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={!pagination.has_prev}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={!pagination.has_next}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">
                    {((currentPage - 1) * pagination.per_page) + 1}
                  </span>{' '}
                  to{' '}
                  <span className="font-medium">
                    {Math.min(currentPage * pagination.per_page, pagination.total)}
                  </span>{' '}
                  of{' '}
                  <span className="font-medium">{pagination.total}</span>{' '}
                  orders
                </p>
              </div>
              
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={!pagination.has_prev}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  
                  {Array.from({ length: pagination.pages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => handlePageChange(page)}
                      className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                        page === currentPage
                          ? 'z-10 bg-emerald-50 border-emerald-500 text-emerald-600'
                          : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                  
                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={!pagination.has_next}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};