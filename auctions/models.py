from django.contrib.auth.models import AbstractUser
from django.db import models




class User(AbstractUser):
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    fee_failure_date = models.DateTimeField(blank=True, null=True)
    profile_picture = models.URLField(blank=True)


class Category(models.Model):
    category = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.category}"
    

class Listing(models.Model):
    date = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    active = models.BooleanField(default=True)
    in_escrow = models.BooleanField(default=False)
    shipped = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    categories = models.ManyToManyField(Category, related_name="listings")
    description = models.TextField()
    image = models.URLField(blank=True)
    starting_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    title = models.CharField(max_length=64)
    closing_date = models.DateTimeField(blank=True, null=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="won_listings", null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.price}"


class Transaction(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_transactions")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_transactions")
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, blank=True, null=True, related_name="transactions")
    notes = models.TextField(max_length=1080, blank=True, null=True)

    def __str__(self):
        return f"{self.date} - {self.amount} - {self.sender} - {self.recipient} - {self.listing}"
    

class Message(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=64, blank=True, null=True)
    message = models.TextField()
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    read = models.BooleanField(default=False)
    deleted_by = models.ManyToManyField(User, related_name="deleted_messages", blank=True)

    def __str__(self):
        return f"{self.sender} - {self.recipient} - {self.message}"
        
    
class Bid(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bids")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    
    def __str__(self):
        return f"{self.amount} - {self.user} - {self.listing}"
    

class Comment(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    anonymous = models.BooleanField(default=False)
    comment = models.TextField()
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")

    def __str__(self):
        return f"{self.comment} - {self.user} - {self.listing}"
    

class Watchlist(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="watchlist")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    
    def __str__(self):
        return f"{self.user} - {self.listing}"