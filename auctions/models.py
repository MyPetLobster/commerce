from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


class Transaction(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_transactions")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_transactions")
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, blank=True, null=True, related_name="transactions")

    def __str__(self):
        return f"{self.sender} - {self.recipient} - {self.amount}"
    

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
        

class Category(models.Model):
    category = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.category}"


class Listing(models.Model):
    active = models.BooleanField(default=True)
    in_escrow = models.BooleanField(default=False)
    shipped = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    categories = models.ManyToManyField(Category, related_name="listings")
    date = models.DateTimeField()
    description = models.TextField()
    image = models.URLField(blank=True)
    starting_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    title = models.CharField(max_length=64)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="listings")
    
    def __str__(self):
        return f"{self.title} - {self.price}"
    
    
class Bid(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bids")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bids")
    
    def __str__(self):
        return f"{self.amount} - {self.user} - {self.listing}"
    

class Comment(models.Model):
    anonymous = models.BooleanField(default=False)
    comment = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")

    def __str__(self):
        return f"{self.comment} - {self.user} - {self.listing}"
    

class Watchlist(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="watchlist")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    
    def __str__(self):
        return f"{self.user} - {self.listing}"
    

class Winner(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="winner")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="winner")
    
    def __str__(self):
        return f"{self.user} - {self.listing}"


