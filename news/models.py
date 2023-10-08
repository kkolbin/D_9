from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError


class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rating = models.IntegerField()

    def send_weekly_notification(self):
        # Logic to fetch new articles published by this author within the last week
        new_articles = Post.objects.filter(author=self.user,
                                           created_at__gte=timezone.now() - timezone.timedelta(days=7))

        if new_articles:
            email_subject = 'Your Weekly Article Summary'
            email_content = 'Here are your new articles published in the last week:\n'
            for article in new_articles:
                article_url = article.get_absolute_url()
                email_content += f'- {article.title}: {article_url}\n'

            send_mail(email_subject, email_content, 'from@example.com', [self.user.email])


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subscribers = models.ManyToManyField(User, related_name='subscribed_categories', blank=True)
    posts = models.ManyToManyField('Post', through='PostCategory')

    def send_weekly_notification(self):
        # Logic to fetch new articles in this category within the last week
        new_articles = Post.objects.filter(categories=self, created_at__gte=timezone.now() - timezone.timedelta(days=7))

        for user in self.subscribers.all():
            if new_articles:
                email_subject = f'New Articles in {self.name} Category'
                email_content = f'Here are the new articles in {self.name} category published in the last week:\n'
                for article in new_articles:
                    article_url = article.get_absolute_url()
                    email_content += f'- {article.title}: {article_url}\n'

                send_mail(email_subject, email_content, 'from@example.com', [user.email])

    def __str__(self):
        return self.name


class PostManager(models.Manager):
    def get_queryset(self):
        return super(PostManager, self).get_queryset().filter(post_type='news')


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post_type_choices = [
        ('news', 'Новость')
    ]
    post_type = models.CharField(max_length=10, choices=post_type_choices)
    created_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(Category, through='PostCategory')
    title = models.CharField(max_length=100)
    content = models.TextField()
    rating = models.IntegerField(default=0)
    objects = PostManager()
    published_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.post_type == 'news' and not self.created_at:
            # Check the number of news articles published by the user today
            today_news_count = Post.objects.filter(author=self.author, post_type='news', created_at__date=timezone.now().date()).count()
            if today_news_count >= 3:
                raise ValidationError("A user can't publish more than three news articles in a day.")

            self.created_at = timezone.now()

        super(Post, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('news:news_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.title


class PostCategory(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('post', 'category')


@receiver(post_save, sender=User)
def add_user_to_common_group(sender, instance, created, **kwargs):
    if created:
        common_group = Group.objects.get(name='common')
        instance.groups.add(common_group)


class LastWeeklyNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_notification_date = models.DateTimeField()
    objects = models.Manager()
