from django.contrib import admin

from website.models import Contact, PrivacyPolicy, TermsOfService, WebsiteInfo, FAQ, Testimonials


@admin.register(WebsiteInfo)
class WebsiteInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'owner', 'logo', 'date_launched')

    def has_add_permission(self, request):
        count = WebsiteInfo.objects.all().count()
        if count == 0:
            return True
        return False


@admin.register(Contact)
class Contact(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'message', 'priority', 'submitted_at', 'is_read')
    list_filter = ('is_read', 'submitted_at', 'priority')
    list_editable = ('is_read',)


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    pass


@admin.register(TermsOfService)
class TermsOfServiceAdmin(admin.ModelAdmin):
    pass


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer', 'order')
    search_fields = ('question', 'answer')
    list_filter = ('is_active',)


@admin.register(Testimonials)
class TestimonialsAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'role', 'school_name', 'school_location', 'rating', 'date_added']
    list_filter = ['rating', 'date_added']
    search_fields = ['full_name', 'message', 'school_name', 'school_location']
