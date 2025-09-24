from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from taggit.managers import TaggableManager

from accounts.models import CustomUser
from core.models import TimestampedModel, SEOModel
from core.utils import (
    FileValidator,
    secure_product_upload_path,
    secure_preview_upload_path,
    secure_thumbnail_upload_path,
    secure_category_image_upload_path,
    secure_product_image_upload_path
)

User = CustomUser


class Category(MPTTModel, TimestampedModel, SEOModel):
    """Hierarchical category model"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(blank=True, null=True, help_text="Flowbite svg icon")
    # Updated to use secure upload path
    image = models.ImageField(
        upload_to=secure_category_image_upload_path,
        blank=True,
        null=True
    )
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Order for display")

    class MPTTMeta:
        order_insertion_by = ['order', 'name']

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # Validate image if present
        if self.image:
            validation_result = FileValidator.validate_image(self.image)
            if not validation_result['is_valid']:
                raise ValidationError(f"Image validation failed: {', '.join(validation_result['errors'])}")

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:category-detail', kwargs={'slug': self.slug})

    def get_product_count(self):
        """Get total products in this category and subcategories"""
        return Product.objects.filter(
            category__in=self.get_descendants(include_self=True),
            status='approved'
        ).count()


class Subject(TimestampedModel):
    """CBC subjects"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Grade(TimestampedModel):
    """CBC grade levels"""
    GRADE_CHOICES = [
        ('pp1', 'PP1'),
        ('pp2', 'PP2'),
        ('grade1', 'Grade 1'),
        ('grade2', 'Grade 2'),
        ('grade3', 'Grade 3'),
        ('grade4', 'Grade 4'),
        ('grade5', 'Grade 5'),
        ('grade6', 'Grade 6'),
        ('grade7', 'Grade 7'),
        ('grade8', 'Grade 8'),
        ('grade9', 'Grade 9'),
        ('form1', 'Form 1'),
        ('form2', 'Form 2'),
        ('form3', 'Form 3'),
        ('form4', 'Form 4'),
    ]

    name = models.CharField(max_length=20, choices=GRADE_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.display_name


class Product(TimestampedModel, SEOModel):
    """Main product model with secure file handling"""
    PRODUCT_TYPES = [
        ('notes', 'Notes'),
        ('scheme', 'Scheme of Work'),
        ('curriculum', 'Curriculum Design'),
        ('guide', 'Teaching Guide'),
        ('assessment', 'Assessment Tool'),
        ('lesson_plan', 'Lesson Plans'),
        ('workbook', 'Workbook'),
        ('textbook', 'Textbook'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(help_text="Brief description for listings")
    content = models.TextField(help_text="Detailed content description")

    # Classification
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='products')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES)

    # Vendor Information
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_free = models.BooleanField(default=False)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         validators=[MinValueValidator(0)])

    # Files with secure upload paths
    preview_file = models.FileField(
        upload_to=secure_preview_upload_path,
        blank=True,
        null=True,
        help_text="Preview file for customers (first few pages)"
    )
    main_file = models.FileField(
        upload_to=secure_product_upload_path,
        help_text="Main product file"
    )
    thumbnail = models.ImageField(
        upload_to=secure_thumbnail_upload_path,
        help_text="Product thumbnail image"
    )
    additional_images = models.ManyToManyField('ProductImage', blank=True, related_name='additional_product_images')

    # Status & Moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_products')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Analytics & Tracking
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)

    # Features
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)

    # SEO and Discoverability
    tags = TaggableManager(blank=True)

    # Store detected file types for reference
    main_file_type = models.CharField(max_length=10, blank=True, help_text="Detected file type")
    preview_file_type = models.CharField(max_length=10, blank=True, help_text="Detected file type")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['subject', 'grade']),
            models.Index(fields=['vendor', 'status']),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        """Custom validation for the model"""
        super().clean()
        errors = {}

        # Validate main file
        if self.main_file:
            validation_result = FileValidator.validate_document(self.main_file)
            if not validation_result['is_valid']:
                errors['main_file'] = validation_result['errors']
            else:
                self.main_file_type = validation_result['detected_type']

        # Validate preview file
        if self.preview_file:
            validation_result = FileValidator.validate_document(self.preview_file)
            if not validation_result['is_valid']:
                errors['preview_file'] = validation_result['errors']
            else:
                self.preview_file_type = validation_result['detected_type']

        # Validate thumbnail
        if self.thumbnail:
            validation_result = FileValidator.validate_image(self.thumbnail)
            if not validation_result['is_valid']:
                errors['thumbnail'] = validation_result['errors']

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        # Set free price
        if self.is_free:
            self.price = 0
            self.discount_price = None

        # Run full validation
        self.full_clean()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:products-detail', kwargs={'slug': self.slug})

    def get_price(self):
        """Get effective price (discount price if available)"""
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def get_discount_percentage(self):
        """Calculate discount percentage"""
        if self.discount_price and self.discount_price < self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    def is_discounted(self):
        """Check if product has discount"""
        return self.discount_price and self.discount_price < self.price

    def increment_views(self):
        """Increment view count"""
        self.view_count = models.F('view_count') + 1
        self.save(update_fields=['view_count'])

    def increment_downloads(self):
        """Increment download count"""
        self.download_count = models.F('download_count') + 1
        self.save(update_fields=['download_count'])

    def update_rating(self):
        """Update average rating based on reviews"""
        reviews = self.reviews.all()
        if reviews:
            total_rating = sum(review.rating for review in reviews)
            self.rating_average = total_rating / len(reviews)
            self.rating_count = len(reviews)
        else:
            self.rating_average = 0
            self.rating_count = 0
        self.save(update_fields=['rating_average', 'rating_count'])

    def get_file_info(self):
        """Get information about uploaded files"""
        return {
            'main_file': {
                'name': self.main_file.name if self.main_file else None,
                'size': self.main_file.size if self.main_file else None,
                'detected_type': self.main_file_type,
            },
            'preview_file': {
                'name': self.preview_file.name if self.preview_file else None,
                'size': self.preview_file.size if self.preview_file else None,
                'detected_type': self.preview_file_type,
            },
            'thumbnail': {
                'name': self.thumbnail.name if self.thumbnail else None,
                'size': self.thumbnail.size if self.thumbnail else None,
            }
        }


class ProductImage(TimestampedModel):
    """Additional product images with secure upload paths"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=secure_product_image_upload_path)
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    detected_type = models.CharField(max_length=10, blank=True, help_text="Detected image type")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.title}"

    def clean(self):
        """Validate the uploaded image"""
        super().clean()
        if self.image:
            validation_result = FileValidator.validate_image(self.image)
            if not validation_result['is_valid']:
                raise ValidationError({'image': validation_result['errors']})
            else:
                self.detected_type = validation_result['detected_type']

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductReview(TimestampedModel):
    """Product reviews and ratings"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    review = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}-star review by {self.user.get_display_name()}"


class ProductViewHistory(TimestampedModel):
    """Track product views for analytics"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='view_history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]