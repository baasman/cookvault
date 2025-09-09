import React, { useState, useEffect } from 'react';
import { InformationCircleIcon } from '@heroicons/react/24/outline';
import type { PrintSpecification } from './PrintOrderModal';

interface PrintSpecificationFormProps {
  printOptions: any;
  bulkPricingTiers: any[];
  specification: PrintSpecification | null;
  quantity: number;
  onSpecificationChange: (spec: PrintSpecification) => void;
  onQuantityChange: (quantity: number) => void;
  onNext: () => void;
  loading: boolean;
}

export const PrintSpecificationForm: React.FC<PrintSpecificationFormProps> = ({
  printOptions,
  bulkPricingTiers,
  specification,
  quantity,
  onSpecificationChange,
  onQuantityChange,
  onNext,
  loading
}) => {
  const [formData, setFormData] = useState<PrintSpecification>({
    trim_size: 'US_TRADE',
    binding_type: 'perfect_bound',
    paper_type: 'standard_white',
    cover_finish: 'matte',
    page_count: 50,
    color_pages: false
  });

  const [showBulkPricing, setShowBulkPricing] = useState(false);
  const [estimatedPageCount, setEstimatedPageCount] = useState(50);

  useEffect(() => {
    if (specification) {
      setFormData(specification);
    } else {
      // Notify parent about default values when no specification is provided
      onSpecificationChange(formData);
    }
  }, [specification]);

  useEffect(() => {
    // Estimate page count based on typical cookbook metrics
    // This could be enhanced to call an API endpoint for better accuracy
    const basePages = 40;
    const averagePagesPerRecipe = 1.5;
    const overhead = 10; // Cover, TOC, index, etc.
    
    // For now, we'll use a default estimate
    setEstimatedPageCount(50);
    setFormData(prev => ({ ...prev, page_count: 50 }));
  }, []);

  const handleInputChange = (field: keyof PrintSpecification, value: any) => {
    const newFormData = { ...formData, [field]: value };
    setFormData(newFormData);
    onSpecificationChange(newFormData);
  };

  const handleQuantityChange = (newQuantity: number) => {
    onQuantityChange(Math.max(1, newQuantity));
  };

  const getBulkDiscountForQuantity = (qty: number) => {
    if (!bulkPricingTiers || bulkPricingTiers.length === 0) return null;
    
    for (const tier of bulkPricingTiers) {
      if (qty >= tier.quantity_min && (tier.quantity_max === null || qty <= tier.quantity_max)) {
        return tier;
      }
    }
    return null;
  };

  const currentDiscount = getBulkDiscountForQuantity(quantity);

  const canProceed = formData.trim_size && formData.binding_type && formData.paper_type && formData.cover_finish && formData.page_count > 0;

  if (loading || !printOptions) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Quantity Selection */}
      <div>
        <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 mb-2">
          Quantity
        </label>
        <div className="flex items-center space-x-4">
          <input
            type="number"
            id="quantity"
            min="1"
            max="1000"
            value={quantity}
            onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 1)}
            className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
          />
          {currentDiscount && (
            <div className="flex items-center text-sm text-emerald-600">
              <span className="font-medium">
                {currentDiscount.discount_percent}% platform fee discount!
              </span>
              <InformationCircleIcon 
                className="h-4 w-4 ml-1 cursor-help" 
                title={currentDiscount.description}
              />
            </div>
          )}
        </div>
        
        {/* Bulk Pricing Tiers */}
        {bulkPricingTiers && bulkPricingTiers.length > 0 && (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setShowBulkPricing(!showBulkPricing)}
              className="text-sm text-emerald-600 hover:text-emerald-700 focus:outline-none"
            >
              {showBulkPricing ? 'Hide' : 'View'} bulk pricing discounts
            </button>
            
            {showBulkPricing && (
              <div className="mt-2 p-3 bg-emerald-50 rounded-md">
                <h4 className="text-sm font-medium text-emerald-900 mb-2">Bulk Pricing Tiers</h4>
                <div className="space-y-1">
                  {bulkPricingTiers.map((tier, index) => (
                    <div key={index} className="text-xs text-emerald-700">
                      {tier.quantity_min}-{tier.quantity_max || '∞'} copies: {tier.discount_percent}% off platform fee
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Trim Size */}
      <div>
        <label htmlFor="trim_size" className="block text-sm font-medium text-gray-700 mb-2">
          Book Size
        </label>
        <select
          id="trim_size"
          value={formData.trim_size}
          onChange={(e) => handleInputChange('trim_size', e.target.value)}
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        >
          {printOptions.trim_sizes?.map((size: any) => (
            <option key={size.value} value={size.value}>
              {size.name}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">
          US Trade (6" × 9") is the most popular size for cookbooks
        </p>
      </div>

      {/* Binding Type */}
      <div>
        <label htmlFor="binding_type" className="block text-sm font-medium text-gray-700 mb-2">
          Binding Style
        </label>
        <select
          id="binding_type"
          value={formData.binding_type}
          onChange={(e) => handleInputChange('binding_type', e.target.value)}
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        >
          {printOptions.binding_types?.map((binding: any) => (
            <option key={binding.value} value={binding.value}>
              {binding.name.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">
          Perfect bound is recommended for cookbooks with 40+ pages
        </p>
      </div>

      {/* Paper Type */}
      <div>
        <label htmlFor="paper_type" className="block text-sm font-medium text-gray-700 mb-2">
          Paper Quality
        </label>
        <select
          id="paper_type"
          value={formData.paper_type}
          onChange={(e) => handleInputChange('paper_type', e.target.value)}
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        >
          {printOptions.paper_types?.map((paper: any) => (
            <option key={paper.value} value={paper.value}>
              {paper.name.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      {/* Cover Finish */}
      <div>
        <label htmlFor="cover_finish" className="block text-sm font-medium text-gray-700 mb-2">
          Cover Finish
        </label>
        <select
          id="cover_finish"
          value={formData.cover_finish}
          onChange={(e) => handleInputChange('cover_finish', e.target.value)}
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        >
          {printOptions.cover_finishes?.map((finish: any) => (
            <option key={finish.value} value={finish.value}>
              {finish.name.charAt(0).toUpperCase() + finish.name.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Page Count */}
      <div>
        <label htmlFor="page_count" className="block text-sm font-medium text-gray-700 mb-2">
          Estimated Page Count
        </label>
        <input
          type="number"
          id="page_count"
          min="20"
          max="500"
          value={formData.page_count}
          onChange={(e) => handleInputChange('page_count', parseInt(e.target.value) || 50)}
          className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">
          This affects printing cost. Final count may vary slightly.
        </p>
      </div>

      {/* Color Pages */}
      <div>
        <div className="flex items-center">
          <input
            id="color_pages"
            type="checkbox"
            checked={formData.color_pages}
            onChange={(e) => handleInputChange('color_pages', e.target.checked)}
            className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
          />
          <label htmlFor="color_pages" className="ml-2 text-sm text-gray-700">
            Include color pages (premium option)
          </label>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Color pages significantly increase printing cost but enhance photo presentation
        </p>
      </div>

      {/* Continue Button */}
      <div className="flex justify-end pt-4">
        <button
          type="button"
          onClick={onNext}
          disabled={!canProceed}
          className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue to Shipping
        </button>
      </div>
    </div>
  );
};